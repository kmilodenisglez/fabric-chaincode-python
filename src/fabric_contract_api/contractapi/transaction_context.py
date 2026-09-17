# SPDX-License-Identifier: Apache-2.0
"""Transaction context for :mod:`fabric_contract_api`.

This module is the Python equivalent of Go's
``contractapi/transaction_context.go``.  It defines:

* :class:`TransactionContextInterface` — an :class:`abc.ABC` describing the
  minimum surface area a transaction context must provide (``get_stub`` and
  ``get_client_identity``).
* :class:`SettableTransactionContextInterface` — an :class:`abc.ABC` that
  adds ``set_stub`` and ``set_client_identity`` so the chaincode dispatcher
  can inject the active :class:`ChaincodeStub` and client identity.
* :class:`TransactionContext` — a default implementation of both interfaces
  that contracts can embed.
* :class:`ClientIdentity` — a minimal client-identity wrapper that mirrors
  the surface area of Go's ``cid.ClientIdentity``.
"""

from __future__ import annotations

import abc
from typing import Any, Optional


class ClientIdentity:
    """Minimal client-identity implementation.

    Mirrors the surface area of Go's ``cid.ClientIdentity`` that the contract
    API relies on.  Built from the proposal metadata decoded by the shim's
    :class:`ChaincodeStub`.
    """

    def __init__(self, stub: Any) -> None:
        self._stub = stub
        self._msp_id: Optional[str] = None
        self._cert: Optional[bytes] = None
        self._attrs: dict = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            creator = self._stub.get_creator()
            if isinstance(creator, dict):
                self._msp_id = creator.get("mspid")
                self._cert = creator.get("idBytes")
        except Exception:
            pass

    def get_mspid(self) -> str:
        """Return the caller's MSP ID."""
        self._ensure_loaded()
        return self._msp_id or ""

    def get_id(self) -> str:
        """Return the caller's DN, base64-encoded.

        Mirrors Go's ``ClientIdentity.GetID``.
        """
        import base64
        self._ensure_loaded()
        if not self._cert:
            raise Exception("Failed to get client identity. Client identity does not have a certificate")
        # Strip PEM headers if present.
        cert = self._cert
        if isinstance(cert, bytes):
            cert_str = cert.decode("utf-8", errors="replace")
        else:
            cert_str = str(cert)
        cert_str = cert_str.replace("-----BEGIN CERTIFICATE-----", "").replace("-----END CERTIFICATE-----", "")
        cert_str = "".join(cert_str.split())
        try:
            raw = base64.b64decode(cert_str)
        except Exception:
            raw = cert_str.encode()
        return base64.b64encode(raw).decode()

    def get_attribute(self, attr_name: str) -> Optional[str]:
        """Return a single attribute from the caller's certificate."""
        self._ensure_loaded()
        return self._attrs.get(attr_name)

    def assert_attribute(self, attr_name: str) -> bool:
        """Return ``True`` if *attr_name* exists in the caller's certificate."""
        self._ensure_loaded()
        return attr_name in self._attrs

    def get_x509(self) -> bytes:
        """Return the raw X.509 certificate bytes of the caller."""
        self._ensure_loaded()
        if not self._cert:
            raise Exception("Client identity does not have a certificate")
        if isinstance(self._cert, str):
            return self._cert.encode()
        return self._cert


class TransactionContextInterface(abc.ABC):
    """Read-only interface for transaction contexts."""

    @abc.abstractmethod
    def get_stub(self) -> Any:
        """Return the active :class:`ChaincodeStub`."""

    @abc.abstractmethod
    def get_client_identity(self) -> ClientIdentity:
        """Return the caller's :class:`ClientIdentity`."""


class SettableTransactionContextInterface(TransactionContextInterface):
    """Interface that adds the setters used by the chaincode dispatcher."""

    @abc.abstractmethod
    def set_stub(self, stub: Any) -> None: ...

    @abc.abstractmethod
    def set_client_identity(self, ci: ClientIdentity) -> None: ...


class TransactionContext(SettableTransactionContextInterface):
    """Default transaction context.

    Contracts that don't need a custom transaction context can simply embed
    :class:`TransactionContext`::

        class MyContract(Contract):
            TransactionContextHandler = TransactionContext

            def my_transaction(self, ctx: TransactionContextInterface) -> str:
                stub = ctx.get_stub()
                ...
    """

    def __init__(self) -> None:
        self._stub: Any = None
        self._client_identity: Optional[ClientIdentity] = None

    def set_stub(self, stub: Any) -> None:
        self._stub = stub

    def set_client_identity(self, ci: ClientIdentity) -> None:
        self._client_identity = ci

    def get_stub(self) -> Any:
        return self._stub

    def get_client_identity(self) -> ClientIdentity:
        if self._client_identity is None:
            self._client_identity = ClientIdentity(self._stub)
        return self._client_identity


__all__ = [
    "ClientIdentity",
    "TransactionContext",
    "TransactionContextInterface",
    "SettableTransactionContextInterface",
]
