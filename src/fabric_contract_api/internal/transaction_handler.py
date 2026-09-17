# SPDX-License-Identifier: Apache-2.0
"""Transaction handler for before/after/unknown transactions.

This is the Python equivalent of Go's ``internal/transaction_handler.go``.
A :class:`TransactionHandler` is a thin specialisation of
:class:`ContractFunction` for the three "lifecycle" hooks every contract can
define:

* ``BeforeTransaction`` — called before the named function.
* ``AfterTransaction`` — called after the named function (and receives its
  return value).
* ``UnknownTransaction`` — called when an unknown function name is requested.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Optional, Tuple

from .contract_function import ContractFunction


class TransactionHandlerType:
    """Enum-like constants for the three handler types."""

    BEFORE = 1
    UNKNOWN = 2
    AFTER = 3

    @staticmethod
    def to_string(value: int) -> str:
        if value == TransactionHandlerType.BEFORE:
            return "Before"
        if value == TransactionHandlerType.AFTER:
            return "After"
        if value == TransactionHandlerType.UNKNOWN:
            return "Unknown"
        raise ValueError("invalid transaction handler type")


class TransactionHandler(ContractFunction):
    """Specialised :class:`ContractFunction` for before/after/unknown hooks."""

    def __init__(self, fn: Callable[..., Any], context_handler_type: Any,
                 handles_type: int) -> None:
        super().__init__(
            fn=fn,
            call_type=0,
            param_details=_empty_params(),
            return_details=_empty_returns(),
        )
        # Re-parse to populate params/returns correctly.
        param_details, return_details = self._parse(fn, context_handler_type)
        self.params = param_details
        self.returns = return_details
        self.handles_type = handles_type

    async def call(self, ctx: Any, data: Any, serializer) -> Tuple[str, Any, Optional[Exception]]:  # type: ignore[override]
        """Invoke the hook.

        For ``TransactionHandlerTypeAfter`` *data* is the success value (or
        ``None``) returned by the named transaction function.
        """
        values = []
        if self.params.context is not None:
            values.append(ctx)

        # Only after-transactions may take the success value as an additional
        # parameter.
        if self.handles_type == TransactionHandlerType.AFTER and len(self.params.fields) == 1:
            if data is None:
                # Mirror Go's behaviour: when the named function returned no
                # success value, pass an "undefined" sentinel.
                from ..contractapi.utils.undefined_interface import UndefinedInterface
                values.append(UndefinedInterface())
            else:
                values.append(data)

        try:
            if inspect.iscoroutinefunction(self.function):
                some_resp = await self.function(*values)
            else:
                some_resp = self.function(*values)
        except Exception as exc:
            return "", None, exc

        return self._handle_response(some_resp, None, None, serializer)


def _empty_params():
    from .contract_function import _ContractFunctionParams
    return _ContractFunctionParams()


def _empty_returns():
    from .contract_function import _ContractFunctionReturns
    return _ContractFunctionReturns()


def new_transaction_handler(fn: Callable[..., Any], context_handler_type: Any,
                              handles_type: int) -> TransactionHandler:
    """Create a new :class:`TransactionHandler`.

    Mirrors Go's ``NewTransactionHandler``.  Raises ``ValueError`` if the
    function does not satisfy the constraints of the requested handler type.
    """
    try:
        th = TransactionHandler(fn, context_handler_type, handles_type)
    except ValueError as exc:
        htype_str = TransactionHandlerType.to_string(handles_type)
        raise ValueError(f"error creating {htype_str}. {exc}") from exc

    if handles_type != TransactionHandlerType.AFTER and len(th.params.fields) > 0:
        htype_str = TransactionHandlerType.to_string(handles_type)
        raise ValueError(
            f"{htype_str} transactions may not take any params other than the transaction context"
        )
    if handles_type == TransactionHandlerType.AFTER and len(th.params.fields) > 1:
        raise ValueError("after transactions must take at most one non-context param")
    # In Python, "interface" matches any type, so we keep the Go constraint
    # simple: the after-transaction may take at most one extra parameter,
    # of any type.

    return th


__all__ = [
    "TransactionHandler",
    "TransactionHandlerType",
    "new_transaction_handler",
]
