# SPDX-License-Identifier: Apache-2.0
"""Contract function wrapper.

This is the Python equivalent of Go's ``internal/contract_function.go``.
A :class:`ContractFunction` wraps a Python callable (typically a method of a
contract class) along with a description of its parameters and return type
so that it can be called by the :class:`ContractChaincode` dispatcher.

Compared to the Go implementation, the Python version does not need to use
runtime reflection (``reflect``) — instead it uses :mod:`inspect` and
:mod:`typing` annotations to extract parameter and return types at
registration time.
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import typing as _t
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..metadata import (
    ComponentMetadata,
    ParameterMetadata,
    ReturnMetadata,
    TransactionMetadata,
)
from ..metadata.schema import get_schema
from ..internal.types_handler import type_is_valid, type_matches_interface
from ..internal.types import ErrorType, TimeType
from ..internal.utils import slice_as_comma_sentence
from .types import BasicTypes


# ---------------------------------------------------------------------------
# CallType enum
# ---------------------------------------------------------------------------


class CallType:
    """Enum-like constants for the call type of a contract function.

    Mirrors Go's ``CallType`` constants.
    """

    NA = 0
    SUBMIT = 1
    EVALUATE = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_optional(tp: Any) -> Any:
    origin = _t.get_origin(tp)
    if origin is _t.Union:
        args = [a for a in _t.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _is_context_type(tp: Any, context_handler_type: Any) -> bool:
    """Return ``True`` if *tp* is the transaction-context type.

    A type is considered the context type when:
    * it equals ``context_handler_type``; or
    * it is an :class:`abc.ABC` protocol and *context_handler_type* structurally
      matches it (mirrors the Go interface check).
    """
    tp = _strip_optional(tp)
    if tp is context_handler_type:
        return True
    # If the parameter type is an abstract base class or a typing.Protocol,
    # check whether the context type implements all of its abstract methods.
    if tp is not None and getattr(tp, "__abstractmethods__", None):
        if type_matches_interface(context_handler_type, tp) is None:
            return True
    return False


def _parse_param(p: inspect.Parameter, method_name: str,
                 context_handler_type: Any) -> Tuple[bool, Any]:
    """Parse a single parameter.

    Returns ``(is_context, type_annotation)``.  *type_annotation* is ``None``
    when the parameter is the transaction context (and thus should not be
    passed as a positional arg from the serializer).
    """
    annotation = p.annotation
    if annotation is inspect.Parameter.empty:
        # No annotation — assume it's the context if it's the first
        # parameter named ``ctx``/``context``; otherwise treat as Any.
        if p.name in ("ctx", "context", "ctx_", "transaction_context"):
            return True, context_handler_type
        return False, _t.Any

    if _is_context_type(annotation, context_handler_type):
        return True, annotation
    return False, annotation


def _parse_method(fn: Callable[..., Any], context_handler_type: Any
                  ) -> Tuple[List[Any], bool, Any, bool]:
    """Parse the signature of *fn*.

    Returns ``(field_types, uses_context, success_type, returns_error)``.
    """
    sig = inspect.signature(fn)
    try:
        hints = _t.get_type_hints(fn)
    except Exception:
        hints = {}

    field_types: List[Any] = []
    uses_context = False

    params = list(sig.parameters.values())
    if params and params[0].name == "self":
        params = params[1:]

    for i, p in enumerate(params):
        annotation = hints.get(p.name, p.annotation)
        if annotation is inspect.Parameter.empty:
            annotation = _t.Any

        is_ctx, tp = _parse_param_named(p, annotation, context_handler_type)
        if is_ctx:
            if i != 0:
                raise ValueError(
                    f"functions requiring the TransactionContext must require it "
                    f"as the first parameter. {fn.__name__} takes it as parameter {i}"
                )
            uses_context = True
            continue

        err = type_is_valid(tp, allow_error=False)
        if err is not None:
            raise ValueError(
                f"{fn.__name__} contains invalid parameter type. {err}"
            )
        field_types.append(tp)

    return_type = hints.get("return", None)
    success_type, returns_error = _parse_return(return_type, fn.__name__)

    return field_types, uses_context, success_type, returns_error


def _parse_param_named(p: inspect.Parameter, annotation: Any,
                       context_handler_type: Any) -> Tuple[bool, Any]:
    """Like :func:`_parse_param` but uses the resolved annotation."""
    if _is_context_type(annotation, context_handler_type):
        return True, annotation
    return False, annotation


def _parse_return(return_type: Any, method_name: str) -> Tuple[Any, bool]:
    """Parse a return annotation.

    Returns ``(success_type, returns_error)``.  ``success_type`` is ``None``
    when the function does not return a value.  ``returns_error`` is ``True``
    when the function declares an error return (a tuple whose last element is
    ``Exception`` / ``BaseException``).

    The Python contract API supports three idioms for returning errors from a
    contract function:

    1. **Raise an exception** — the simplest, most Pythonic form.  The
       function's return type annotation is the success type only.
    2. **Return ``(value, exception_or_None)``** — a Go-style tuple.  The
       return annotation is ``Tuple[T, Optional[Exception]]``.  When the
       exception is ``None`` the success value is used; otherwise the
       exception is propagated.
    3. **Return ``Optional[T]`` and raise on ``None``** — equivalent to
       form 1 for type-checking purposes.
    """
    if return_type is None or return_type is inspect.Parameter.empty:
        return None, False
    if return_type is type(None):
        return None, False

    return_type = _strip_optional(return_type)
    origin = _t.get_origin(return_type)
    args = _t.get_args(return_type)

    if origin is tuple or origin is _t.Tuple:
        if not args:
            return None, True
        success = args[0]
        if len(args) == 2 and (args[1] is Exception or args[1] is BaseException):
            return success, True
        if len(args) == 2:
            # Treat the second element as an error type if it's a subclass of
            # BaseException, otherwise as a regular success type pair.
            second = args[1]
            if isinstance(second, type) and issubclass(second, BaseException):
                return success, True
            return return_type, False
        return return_type, False

    if isinstance(return_type, type) and issubclass(return_type, BaseException):
        return None, True

    return return_type, False


# ---------------------------------------------------------------------------
# ContractFunction
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _ContractFunctionParams:
    context: Optional[Any] = None  # the type annotation of the context, or None
    fields: List[Any] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class _ContractFunctionReturns:
    success: Optional[Any] = None
    error: bool = False


class ContractFunction:
    """Wraps a callable so that it can be dispatched by the chaincode.

    Public attributes mirror Go's ``ContractFunction``:

    * ``function`` — the underlying callable.
    * ``call_type`` — one of :class:`CallType` constants.
    * ``params`` — a :class:`_ContractFunctionParams` describing the parameters.
    * ``returns`` — a :class:`_ContractFunctionReturns` describing the return.
    """

    def __init__(self, fn: Callable[..., Any], call_type: int,
                 param_details: _ContractFunctionParams,
                 return_details: _ContractFunctionReturns) -> None:
        self.function = fn
        self.call_type = call_type
        self.params = param_details
        self.returns = return_details

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_callable(cls, fn: Callable[..., Any], call_type: int,
                      context_handler_type: Any) -> "ContractFunction":
        """Build a :class:`ContractFunction` from an arbitrary callable.

        Mirrors Go's ``NewContractFunctionFromFunc``.
        """
        if not callable(fn):
            raise TypeError(
                f"cannot create new contract function from {type(fn).__name__}. "
                "Can only use callable"
            )
        param_details, return_details = cls._parse(fn, context_handler_type)
        return cls(fn, call_type, param_details, return_details)

    @classmethod
    def from_method(cls, instance: Any, method_name: str, call_type: int,
                    context_handler_type: Any) -> "ContractFunction":
        """Build a :class:`ContractFunction` from a method on *instance*.

        Mirrors Go's ``NewContractFunctionFromReflect``.
        """
        fn = getattr(instance, method_name)
        return cls.from_callable(fn, call_type, context_handler_type)

    @staticmethod
    def _parse(fn: Callable[..., Any], context_handler_type: Any
                ) -> Tuple[_ContractFunctionParams, _ContractFunctionReturns]:
        try:
            field_types, uses_context, success_type, returns_error = _parse_method(
                fn, context_handler_type
            )
        except ValueError:
            raise
        return (
            _ContractFunctionParams(
                context=context_handler_type if uses_context else None,
                fields=field_types,
            ),
            _ContractFunctionReturns(success=success_type, error=returns_error),
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def reflect_metadata(self, name: str,
                          existing_components: ComponentMetadata) -> TransactionMetadata:
        """Return the metadata describing this function.

        Mirrors Go's ``ContractFunction.ReflectMetadata``.
        """
        tx_metadata = TransactionMetadata(name=name, tag=[])
        tx_type = "SUBMIT"
        tx_type_deprecated = "submit"
        if self.call_type == CallType.EVALUATE:
            tx_type = "EVALUATE"
            tx_type_deprecated = "evaluate"
        tx_metadata.tag = [tx_type_deprecated, tx_type]

        for index, field in enumerate(self.params.fields):
            schema = get_schema(field, existing_components)
            param = ParameterMetadata(name=f"param{index}", schema=schema)
            tx_metadata.parameters.append(param)

        if self.returns.success is not None:
            schema = get_schema(self.returns.success, existing_components)
            tx_metadata.returns = ReturnMetadata(schema=schema)

        return tx_metadata

    # ------------------------------------------------------------------
    # Calling
    # ------------------------------------------------------------------

    async def call(self, ctx: Any, supplementary_metadata: Optional[TransactionMetadata],
                    components: Optional[ComponentMetadata], serializer, *params: str
                    ) -> Tuple[str, Any, Optional[Exception]]:
        """Invoke the wrapped function with the given string parameters.

        Returns ``(success_string, success_value, error)`` — mirroring Go's
        ``ContractFunction.Call``.
        """
        parameter_metadata: Optional[List[ParameterMetadata]] = None
        if supplementary_metadata is not None:
            parameter_metadata = supplementary_metadata.parameters

        try:
            values = self._format_args(ctx, parameter_metadata, components,
                                        list(params), serializer)
        except Exception as exc:
            return "", None, exc

        # Invoke the underlying function.  Both sync and async callables are
        # supported.
        try:
            if inspect.iscoroutinefunction(self.function):
                raw_response = await self.function(*values)
            else:
                raw_response = self.function(*values)
        except Exception as exc:
            return "", None, exc

        returns_metadata = None
        if supplementary_metadata is not None:
            returns_metadata = supplementary_metadata.returns

        return self._handle_response(raw_response, returns_metadata, components, serializer)

    # ------------------------------------------------------------------
    # Argument formatting
    # ------------------------------------------------------------------

    def _format_args(self, ctx: Any,
                      supplementary_metadata: Optional[List[ParameterMetadata]],
                      components: Optional[ComponentMetadata],
                      params: List[str], serializer) -> List[Any]:
        """Convert the list of string parameters into typed Python values."""
        num_params = len(self.params.fields)

        if supplementary_metadata is not None and len(supplementary_metadata) != num_params:
            raise ValueError(
                f"incorrect number of params in supplementary metadata. "
                f"Expected {num_params}, received {len(supplementary_metadata)}"
            )

        values: List[Any] = []
        if self.params.context is not None:
            values.append(ctx)

        if len(params) < num_params:
            raise ValueError(
                f"incorrect number of params. Expected {num_params}, received {len(params)}"
            )

        for i in range(num_params):
            field_type = self.params.fields[i]
            param_metadata = supplementary_metadata[i] if supplementary_metadata else None
            value, err = serializer.from_string(
                params[i], field_type, param_metadata, components,
            )
            if err is not None:
                param_name = ""
                if param_metadata is not None:
                    param_name = " " + param_metadata.name
                raise ValueError(
                    f"error managing parameter{param_name}. {err}"
                ) from err
            values.append(value)

        return values

    # ------------------------------------------------------------------
    # Response handling
    # ------------------------------------------------------------------

    def _handle_response(self, response: Any,
                          returns_metadata: Optional[ReturnMetadata],
                          components: Optional[ComponentMetadata],
                          serializer) -> Tuple[str, Any, Optional[Exception]]:
        """Validate and serialise the function's return value.

        Supports:
        * no return -> ``("", None, None)``
        * single success value -> ``(stringified, value, None)``
        * Go-style ``(value, exception_or_None)`` tuple -> success + error
        """
        success_response: Any = None
        error_response: Optional[BaseException] = None

        if self.returns.error and isinstance(response, tuple) and len(response) == 2:
            success_response = response[0]
            err = response[1]
            if isinstance(err, BaseException):
                error_response = err
            elif err is not None:
                # The "error" slot was a non-exception — treat as a success-only return.
                success_response = response
        else:
            success_response = response

        success_string = ""
        iface: Any = None

        if self.returns.success is not None and success_response is not None:
            if serializer is not None:
                s, err = serializer.to_string(
                    success_response, self.returns.success,
                    returns_metadata, components,
                )
                if err is not None:
                    wrapped = ValueError(
                        f"error handling success response. {err}"
                    )
                    wrapped.__cause__ = err
                    return "", None, wrapped
                success_string = s
            iface = success_response

        return success_string, iface, error_response


__all__ = ["CallType", "ContractFunction"]
