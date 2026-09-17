# SPDX-License-Identifier: Apache-2.0
"""Static type validation for contract functions.

This module is the Python equivalent of Go's
``fabric-contract-api-go/internal/types_handler``.  The goal is to walk
through every parameter and return annotation of a contract's transaction
function and verify that each one is a type the contract API can serialise.

Allowed parameter types are:

* the basic scalar types (``str``, ``bool``, ``int``, ``float``)
* ``bytes`` / ``bytearray`` (treated as raw byte strings)
* ``list[T]`` / ``typing.List[T]`` where ``T`` is itself an allowed type
* ``dict[str, V]`` / ``typing.Dict[str, V]`` where ``V`` is allowed
* arbitrary dataclasses or plain classes (treated as structured objects and
  serialised as JSON)
* ``typing.Any`` / ``object`` — accepted as opaque strings
* :class:`datetime.datetime` — accepted as an RFC3339-formatted timestamp
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import typing as _t
from typing import Any, List, Optional, Sequence, Tuple, Type

from . import types as _types
from .utils import slice_as_comma_sentence


def _basic_types_as_slice() -> List[str]:
    """Return a sorted list of the basic-type names."""
    return sorted(t.__name__ for t in _types.BasicTypes)


def list_basic_types() -> str:
    """Return a comma-and-and sentence of the supported basic types."""
    return slice_as_comma_sentence(_basic_types_as_slice())


def _origin_is(tp: Any, origin: Any) -> bool:
    """True if *tp*'s typing origin is *origin*.

    Examples:
        ``_origin_is(list[int], list)`` -> True
        ``_origin_is(dict[str, int], dict)`` -> True
    """
    return _t.get_origin(tp) is origin


def _type_kind(tp: Any) -> str:
    """Return a human-friendly kind name for *tp*."""
    if _t.get_origin(tp) is not None:
        return str(_t.get_origin(tp))
    if isinstance(tp, type):
        return tp.__name__
    return str(tp)


def _strip_optional(tp: Any) -> Any:
    """Strip a ``typing.Optional[X]`` / ``typing.Union[X, None]`` wrapper.

    The contract API treats ``Optional[X]`` the same as ``X`` for the purposes
    of validation (a missing argument coming through as ``""`` is still
    converted to the zero-value of ``X``).
    """
    origin = _t.get_origin(tp)
    if origin is _t.Union:
        args = [a for a in _t.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def type_is_valid(tp: Any, additional_types: Optional[Sequence[Any]] = None,
                  allow_error: bool = False) -> Optional[str]:
    """Validate that *tp* is a type the contract API can serialise.

    Returns ``None`` when the type is valid, or an error message otherwise.

    Args:
        tp: The type to validate (a ``type`` instance, a ``typing`` alias,
            or :data:`typing.Any`).
        additional_types: A list of types that should additionally be allowed
            (used for cyclic struct references).
        allow_error: When ``True`` the sentinel :data:`types.ErrorType` is
            also accepted as a valid type — this is used when validating
            *return* types of contract functions.
    """
    additional_types = list(additional_types or [])

    # Unwrap Optional[X] -> X
    tp = _strip_optional(tp)

    if tp is _t.Any or tp is object:
        return None

    # typing.List / typing.Dict / typing.Tuple etc.
    origin = _t.get_origin(tp)
    args = _t.get_args(tp)

    if origin is list or origin is _t.List:
        if not args:
            return "list must have an element type, e.g. list[str]"
        return type_is_valid(args[0], additional_types, False)

    if origin is dict or origin is _t.Dict:
        if not args or len(args) != 2:
            return "map must have exactly two type arguments, e.g. dict[str, int]"
        key_type, value_type = args
        if key_type is not str:
            return f"map key type {_type_kind(key_type)} is not valid. Expected string"
        return type_is_valid(value_type, additional_types, False)

    if origin is tuple or origin is _t.Tuple:
        if not args:
            return "tuples must have at least one element"
        for arg in args:
            err = type_is_valid(arg, additional_types, False)
            if err:
                return err
        return None

    # bytes / bytearray
    if _types.is_bytes(tp):
        return None

    # datetime
    if tp is _dt.datetime or tp is _dt.date:
        return None

    # Basic scalar
    if tp in _types.BasicTypes:
        return None

    # Cyclic structs already in additional_types
    if tp in additional_types:
        return None

    # Sentinel for the error return type
    if tp is _types.ErrorType:
        if allow_error:
            return None
        return f"type {tp!r} is not valid as a parameter"

    # Struct: dataclass or plain class
    if isinstance(tp, type):
        if dataclasses.is_dataclass(tp) or hasattr(tp, "__dict__"):
            new_additional = list(additional_types) + [tp]
            return _struct_of_valid_type(tp, new_additional)

    err_str = " error," if allow_error else ""
    return (f"type {_type_kind(tp)} is not valid. Expected a struct or one of "
            f"the basic types{err_str} {list_basic_types()} or an array/slice of these")


def _struct_of_valid_type(tp: Type[Any], additional_types: Sequence[Any]) -> Optional[str]:
    """Validate each field of a struct (dataclass or plain class).

    Plain classes have their ``__init__`` parameters inspected (so that
    user-defined ``__init__`` methods can drive the schema); dataclasses are
    inspected through their declared fields.
    """
    if dataclasses.is_dataclass(tp):
        # Resolve PEP 563 string annotations to actual types.
        try:
            hints = _t.get_type_hints(tp)
        except Exception:
            hints = {}
        fields = dataclasses.fields(tp)
        for field in fields:
            resolved_type = hints.get(field.name, field.type)
            err = type_is_valid(resolved_type, additional_types, False)
            if err:
                return err
        return None

    # Plain class — inspect __init__ annotations if present.
    try:
        hints = _t.get_type_hints(tp.__init__)
    except Exception:
        hints = {}
    for name, hint in hints.items():
        if name == "self":
            continue
        if name == "return":
            continue
        err = type_is_valid(hint, additional_types, False)
        if err:
            return err
    return None


def type_matches_interface(to_match: Any, iface: Any) -> Optional[str]:
    """Check whether *to_match* structurally satisfies the *iface* protocol.

    Mirrors ``typeMatchesInterface`` from the Go implementation.  In Python we
    rely on :class:`typing.Protocol` and :func:`typing.runtime_checkable` to
    do this — but also fall back to method-name comparison for plain
    :class:`abc.ABC` subclasses, which is how :class:`TransactionContextInterface`
    is defined.
    """
    if iface is None:
        return "type passed for interface is not an interface"
    if not getattr(iface, "__abstractmethods__", None) and not _t.is_protocol(iface):
        return "type passed for interface is not an interface"

    expected_methods = getattr(iface, "__abstractmethods__", frozenset())
    for method_name in expected_methods:
        if not hasattr(to_match, method_name):
            return f"missing function {method_name}"
    return None


def _is_protocol(tp: Any) -> bool:
    return _t.is_protocol(tp) if hasattr(_t, "is_protocol") else False


__all__ = [
    "list_basic_types",
    "type_is_valid",
    "type_matches_interface",
]
