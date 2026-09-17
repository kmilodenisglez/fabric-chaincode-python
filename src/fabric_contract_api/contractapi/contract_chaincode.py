# SPDX-License-Identifier: Apache-2.0
"""High-level contract chaincode.

This is the Python equivalent of Go's ``contractapi/contract_chaincode.go``.
It implements the :class:`fabric_shim.Chaincode` interface and dispatches
incoming Init/Invoke transactions to the appropriate registered contract's
transaction functions.

Typical usage::

    from fabric_contract_api.contractapi import Contract, ContractChaincode
    from fabric_shim import start

    class MyContract(Contract):
        Name = "MyContract"

        def my_transaction(self, ctx, key: str) -> str:
            ...

    if __name__ == "__main__":
        cc = ContractChaincode.new_chaincode(MyContract())
        cc.start()
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.fabric_shim.interfaces import Chaincode, ChaincodeStubInterface
from src.fabric_shim.response import ResponseCode, success as _shim_success, error as _shim_error

from ..internal.contract_function import CallType, ContractFunction
from ..internal.transaction_handler import (
    TransactionHandler,
    TransactionHandlerType,
    new_transaction_handler,
)
from ..internal.utils import string_in_slice
from ..metadata import (
    ComponentMetadata,
    ContractChaincodeMetadata,
    ContractMetadata,
    InfoMetadata,
    TransactionMetadata,
    read_metadata_file,
    validate_against_schema,
)
from ..serializer import JSONSerializer, TransactionSerializer
from .contract import (
    Contract,
    ContractInterface,
    EvaluationContractInterface,
    IgnoreContractInterface,
)
from .system_contract import SystemContract, SystemContractName
from .transaction_context import (
    ClientIdentity,
    TransactionContext
)


#: Environment variable that holds the chaincode server address.
SERVER_ADDRESS_VARIABLE = "CHAINCODE_SERVER_ADDRESS"
#: Environment variable that holds the chaincode ID name.
CHAINCODE_ID_VARIABLE = "CORE_CHAINCODE_ID_NAME"


# ---------------------------------------------------------------------------
# Internal: per-contract metadata used by the dispatcher
# ---------------------------------------------------------------------------


class _ContractChaincodeContract:
    """Internal record describing one registered contract."""

    def __init__(self) -> None:
        self.info: InfoMetadata = InfoMetadata()
        self.functions: Dict[str, ContractFunction] = {}
        self.unknown_transaction: Optional[TransactionHandler] = None
        self.before_transaction: Optional[TransactionHandler] = None
        self.after_transaction: Optional[TransactionHandler] = None
        self.transaction_context_handler: type = TransactionContext


# ---------------------------------------------------------------------------
# ContractChaincode
# ---------------------------------------------------------------------------


class ContractChaincode(Chaincode):
    """Chaincode adapter that dispatches to registered contracts."""

    DefaultContract: str = ""
    Info: InfoMetadata = InfoMetadata()
    TransactionSerializer: TransactionSerializer = JSONSerializer()

    def __init__(self) -> None:
        # We don't call ``super().__init__`` because ``Chaincode`` is abstract
        # and our intent is to provide concrete implementations of ``init``
        # and ``invoke``.
        self._contracts: Dict[str, _ContractChaincodeContract] = {}
        self._metadata: ContractChaincodeMetadata = ContractChaincodeMetadata()
        self._system_contract: SystemContract = SystemContract()
        self._ci_methods: List[str] = _get_ci_methods()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def new_chaincode(cls, *contracts: ContractInterface) -> "ContractChaincode":
        """Create a new :class:`ContractChaincode` from one or more contracts.

        Mirrors Go's ``NewChaincode``.
        """
        cc = cls()
        for contract in contracts:
            additional_excludes: List[str] = []
            # Mirror Go's duck-typing: if the contract exposes
            # ``get_ignored_functions`` we treat it as an
            # ``IgnoreContractInterface``.
            ignored_fn = getattr(contract, "get_ignored_functions", None)
            if callable(ignored_fn):
                try:
                    additional_excludes = list(ignored_fn() or [])
                except Exception:
                    additional_excludes = []
            err = cc._add_contract(contract, cc._ci_methods + additional_excludes)
            if err is not None:
                raise err

        # System contract
        cc._system_contract = SystemContract()
        cc._system_contract.Name = SystemContractName
        err = cc._add_contract(cc._system_contract, cc._ci_methods)
        if err is not None:
            raise err

        err = cc._augment_metadata()
        if err is not None:
            raise err

        metadata_json = cc._metadata.to_json()
        cc._system_contract._set_metadata(metadata_json)
        cc.TransactionSerializer = JSONSerializer()
        return cc

    def start(self, cc_id: Optional[str] = None, address: Optional[str] = None,
              key: Optional[bytes] = None, cert: Optional[bytes] = None,
              client_ca_certs: Optional[bytes] = None) -> None:
        """Start the chaincode in the Fabric shim.

        Reads the chaincode ID and server address from the environment when
        not explicitly provided, mirroring Go's ``ContractChaincode.Start``.
        """
        # Local import to avoid a hard dependency cycle when this module is
        # imported eagerly by user code.
        from src.fabric_shim import start as _shim_start

        _shim_start(
            cc=self,
            cc_id=cc_id,
            address=address,
            key=key,
            cert=cert,
            client_ca_certs=client_ca_certs,
        )

    # ------------------------------------------------------------------
    # Chaincode interface
    # ------------------------------------------------------------------

    async def init(self, stub: ChaincodeStubInterface):
        """Handle the Init transaction.

        Mirrors Go's ``Init``.  When a function name is supplied (e.g. when
        the chaincode container is instantiated with ``{Init, args}``), this
        method delegates to :meth:`invoke`.  Otherwise it returns a default
        success message.
        """
        try:
            ns_fcn, _ = _get_function_and_parameters(stub)
        except Exception:
            ns_fcn = ""

        if not ns_fcn:
            return _shim_success(b"Default initiator successful.")
        return await self.invoke(stub)

    async def invoke(self, stub: ChaincodeStubInterface):
        """Handle the Invoke transaction.

        Mirrors Go's ``Invoke``.
        """
        ns, fn, params = self._get_namespace_function_and_params(stub)

        ns_contract = self._contracts.get(ns)
        if ns_contract is None:
            return _shim_error_response(f"Contract not found with name {ns}")

        if not fn:
            return _shim_error_response("Blank function name passed")

        ctx = ns_contract.transaction_context_handler()
        ctx.set_stub(stub)
        ctx.set_client_identity(ClientIdentity(stub))

        # Before-transaction
        if ns_contract.before_transaction is not None:
            _, _, err_res = await ns_contract.before_transaction.call(ctx, None, self.TransactionSerializer)
            if err_res is not None:
                return _shim_error_response(str(err_res))

        # Look up the named function.  Method names are case-sensitive —
        # the contract API uses the original Python method names (typically
        # snake_case).  Callers may also use the capitalised Go-style form
        # (``Create`` vs ``create``) for backwards-compatibility.
        contract_fn = ns_contract.functions.get(fn) or ns_contract.functions.get(_to_first_rune_upper_case(fn))
        success_return = ""
        success_iface: Any = None
        error_return: Optional[BaseException] = None

        if contract_fn is None:
            unknown = ns_contract.unknown_transaction
            if unknown is None:
                return _shim_error_response(
                    f"Function {fn} not found in contract {ns}"
                )
            success_return, success_iface, error_return = await unknown.call(
                ctx, None, self.TransactionSerializer
            )
        else:
            transaction_schema: Optional[TransactionMetadata] = None
            contract_meta = self._metadata.contracts.get(ns)
            if contract_meta is not None:
                for tx in contract_meta.transactions:
                    if tx.name == fn or tx.name == _to_first_rune_upper_case(fn):
                        transaction_schema = tx
                        break

            success_return, success_iface, error_return = await contract_fn.call(
                ctx, transaction_schema, self._metadata.components,
                self.TransactionSerializer, *params,
            )

        if error_return is not None:
            return _shim_error_response(str(error_return))

        # After-transaction
        if ns_contract.after_transaction is not None:
            _, _, err_res = await ns_contract.after_transaction.call(
                ctx, success_iface, self.TransactionSerializer
            )
            if err_res is not None:
                return _shim_error_response(str(err_res))

        payload = success_return.encode("utf-8") if isinstance(success_return, str) else bytes(success_return)
        return _shim_success(payload)

    # ------------------------------------------------------------------
    # Internal: contract registration
    # ------------------------------------------------------------------

    def _add_contract(self, contract: ContractInterface,
                       exclude_funcs: List[str]) -> Optional[Exception]:
        """Register *contract* with this chaincode.

        Mirrors Go's ``addContract``.  Returns ``None`` on success or an
        ``Exception`` describing the failure.
        """
        ns = contract.get_name() or type(contract).__name__
        if not ns:
            return ValueError("contract must have a name")
        if ns in self._contracts:
            return ValueError(
                f"multiple contracts being merged into chaincode with name {ns}"
            )

        ccn = _ContractChaincodeContract()

        # Resolve the transaction-context handler.
        ctx_handler = contract.get_transaction_context_handler()
        if isinstance(ctx_handler, type):
            ccn.transaction_context_handler = ctx_handler
        else:
            ccn.transaction_context_handler = type(ctx_handler)

        ccn.info = contract.get_info() or InfoMetadata()
        if not ccn.info.version:
            ccn.info.version = "latest"
        if not ccn.info.title:
            ccn.info.title = ns

        # Before / After / Unknown transaction hooks.
        ut = contract.get_unknown_transaction()
        if ut is not None:
            try:
                ccn.unknown_transaction = new_transaction_handler(
                    ut, ccn.transaction_context_handler,
                    TransactionHandlerType.UNKNOWN,
                )
            except Exception as exc:
                return exc

        bt = contract.get_before_transaction()
        if bt is not None:
            try:
                ccn.before_transaction = new_transaction_handler(
                    bt, ccn.transaction_context_handler,
                    TransactionHandlerType.BEFORE,
                )
            except Exception as exc:
                return exc

        at = contract.get_after_transaction()
        if at is not None:
            try:
                ccn.after_transaction = new_transaction_handler(
                    at, ccn.transaction_context_handler,
                    TransactionHandlerType.AFTER,
                )
            except Exception as exc:
                return exc

        evaluate_methods: List[str] = []
        # Mirror Go's duck-typing: if the contract exposes
        # ``get_evaluate_transactions`` we treat it as an
        # ``EvaluationContractInterface``.
        evaluate_fn = getattr(contract, "get_evaluate_transactions", None)
        if callable(evaluate_fn):
            try:
                evaluate_methods = list(evaluate_fn() or [])
            except Exception:
                evaluate_methods = []

        # Walk every public method on the contract instance.
        for method_name in dir(contract):
            if method_name.startswith("_"):
                continue
            if string_in_slice(method_name, exclude_funcs):
                continue
            attr = getattr(contract, method_name, None)
            if not callable(attr):
                continue
            # Skip callables that came from the Contract base class itself
            # (they're already covered by _ci_methods).
            if _is_contract_interface_method(method_name):
                continue

            call_type = CallType.EVALUATE if string_in_slice(method_name, evaluate_methods) else CallType.SUBMIT
            try:
                ccn.functions[method_name] = ContractFunction.from_callable(
                    attr, call_type, ccn.transaction_context_handler,
                )
            except Exception as exc:
                wrapped = ValueError(
                    f"error registering method {method_name} on contract {ns}: {exc}"
                )
                wrapped.__cause__ = exc
                return wrapped

        if not ccn.functions:
            return ValueError(
                f"contracts are required to have at least 1 (non-ignored) public method. "
                f"Contract {ns} has none. Method names that have been ignored: "
                f"{', '.join(exclude_funcs) or '(none)'}"
            )

        self._contracts[ns] = ccn
        if not self.DefaultContract:
            self.DefaultContract = ns
        return None

    # ------------------------------------------------------------------
    # Internal: metadata
    # ------------------------------------------------------------------

    def _reflect_metadata(self) -> ContractChaincodeMetadata:
        reflected = ContractChaincodeMetadata()
        reflected.contracts = {}
        reflected.components = ComponentMetadata()
        reflected.info = self.Info

        # Make a defensive copy so we don't mutate ``self.Info``.
        if reflected.info is not None:
            reflected.info = InfoMetadata(
                description=reflected.info.description,
                title=reflected.info.title,
                contact=reflected.info.contact,
                license=reflected.info.license,
                version=reflected.info.version,
                terms_of_service=reflected.info.terms_of_service,
            )
            if not reflected.info.version:
                reflected.info.version = "latest"
            if not reflected.info.title:
                reflected.info.title = "undefined"

        for key, contract in self._contracts.items():
            contract_meta = ContractMetadata()
            contract_meta.name = key
            contract_meta.info = contract.info
            if self.DefaultContract == key:
                contract_meta.default = True

            for fn_name, fn in contract.functions.items():
                fn_meta = fn.reflect_metadata(fn_name, reflected.components)
                contract_meta.transactions.append(fn_meta)

            contract_meta.transactions.sort(key=lambda t: t.name)
            reflected.contracts[key] = contract_meta

        return reflected

    def _augment_metadata(self) -> Optional[Exception]:
        """Merge reflected metadata with the optional user-supplied file."""
        try:
            file_metadata = read_metadata_file()
            file_not_found = False
        except FileNotFoundError:
            file_metadata = ContractChaincodeMetadata()
            file_not_found = True

        reflected_metadata = self._reflect_metadata()
        file_metadata.append(reflected_metadata)
        err = file_metadata.compile_schemas()
        if err is not None:
            return err
        err = validate_against_schema(file_metadata)
        if err is not None:
            return err
        self._metadata = file_metadata
        return None

    # ------------------------------------------------------------------
    # Internal: routing
    # ------------------------------------------------------------------

    def _get_namespace_function_and_params(self, stub: ChaincodeStubInterface) -> Tuple[str, str, List[str]]:
        ns_fcn, params = _get_function_and_parameters(stub)
        # Split on the last ':' so that contract names with embedded colons
        # are still handled.
        idx = ns_fcn.rfind(":")
        if idx == -1:
            return self.DefaultContract, ns_fcn, params
        return ns_fcn[:idx], ns_fcn[idx + 1:], params


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_ci_methods() -> List[str]:
    """Return the names of every method defined on the contract interfaces."""
    methods: List[str] = []
    seen = set()
    for iface in (ContractInterface, IgnoreContractInterface, EvaluationContractInterface):
        for name in getattr(iface, "__abstractmethods__", frozenset()):
            if name not in seen:
                methods.append(name)
                seen.add(name)
        # Also pick up non-abstract public methods on the base classes
        # (e.g. Contract.get_info is a concrete implementation).
        for name in dir(iface):
            if name.startswith("_"):
                continue
            if name in seen:
                continue
            attr = getattr(iface, name, None)
            if callable(attr):
                methods.append(name)
                seen.add(name)
    # The Contract base class also has the public attributes (Name, Info,
    # ...) — but those aren't methods, so we only need to consider callables.
    for name in dir(Contract):
        if name.startswith("_"):
            continue
        if name in seen:
            continue
        attr = getattr(Contract, name, None)
        if callable(attr):
            methods.append(name)
            seen.add(name)
    return methods


def _is_contract_interface_method(name: str) -> bool:
    """Return ``True`` if *name* is a method defined on a contract interface."""
    for iface in (ContractInterface, IgnoreContractInterface, EvaluationContractInterface, Contract):
        if name in dir(iface):
            return True
    return False


def _to_first_rune_upper_case(text: str) -> str:
    """Capitalize the first character of *text*.

    Mirrors Go's ``toFirstRuneUpperCase``.  Used so that callers can refer to
    a transaction by either ``"myTransaction"`` or ``"mytransaction"`` —
    Python convention is typically lower-case but we want to be lenient.
    """
    if not text:
        return text
    if text[0].isupper():
        return text
    return text[0].upper() + text[1:]


def _get_function_and_parameters(stub: ChaincodeStubInterface) -> Tuple[str, List[str]]:
    """Return ``(function_name, params)`` from the chaincode stub.

    The shim already provides ``get_function_and_parameters`` but raises when
    called without arguments — we wrap it to make it safer.
    """
    try:
        fcn, params = stub.get_function_and_parameters()
        return fcn, list(params)
    except Exception:
        return "", []


def _shim_error_response(msg: str):
    """Build a ``shim.Error()``-equivalent response.

    The existing shim's ``error()`` helper does not accept a message, so we
    build the protobuf ``Response`` directly here.
    """
    from fabric_protos.peer import proposal_response_pb2 as pb
    return pb.Response(status=ResponseCode.ERROR, message=msg.encode("utf-8"))


__all__ = ["ContractChaincode"]
