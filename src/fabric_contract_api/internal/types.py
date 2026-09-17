# SPDX-License-Identifier: Apache-2.0
"""Basic type converters used by the JSON transaction serializer.

This module is the Python equivalent of Go's
``fabric-contract-api-go/internal/types`` package.  Each basic Python type
has a small adapter that knows how to:

1. Convert a ``str`` parameter coming from the Fabric transaction payload
   into the underlying Python type (``int``, ``float``, ``bool``, ...).
2. Produce a JSON-schema snippet (OpenAPI-style) describing the type so that
   it can be embedded into the chaincode metadata.

The Go implementation ships separate converters for ``int8``/``int16``/
``int32``/``int64``/``uint8``/.../``uint64``/``float32``/``float64``.  In
Python the only relevant numeric types are :class:`int` and :class:`float`,
so we collapse the integer family onto ``int`` (unbounded) and the float
family onto ``float`` (IEEE-754 double precision).
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Callable, Dict, Optional, Tuple, Type

# ``inspect`` annotations store classes (and ``typing`` aliases).  We use
# ``type`` as a plain alias throughout this module for readability.
TypeT = Type[Any]


class _BasicType:
    """Adapter for a single basic Python type.

    Subclasses set :attr:`python_type` and override :meth:`convert` and
    :meth:`get_schema`.
    """

    python_type: TypeT = object

    def convert(self, value: str) -> Any:  # pragma: no cover - overridden
        raise NotImplementedError

    def get_schema(self) -> Dict[str, Any]:
        raise NotImplementedError


class _StringType(_BasicType):
    python_type = str

    def convert(self, value: str) -> str:
        return value

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "string"}


class _BoolType(_BasicType):
    python_type = bool

    def convert(self, value: str) -> bool:
        if value == "":
            return False
        # Python's bool() would return True for any non-empty string, but we
        # want strict parsing here so that "false" really means False.
        lowered = value.strip().lower()
        if lowered in ("true", "t", "1", "yes", "y"):
            return True
        if lowered in ("false", "f", "0", "no", "n"):
            return False
        raise ValueError(f"cannot convert passed value {value!r} to bool")

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "boolean"}


class _IntType(_BasicType):
    python_type = int

    def convert(self, value: str) -> int:
        if value == "":
            return 0
        try:
            return int(value, 10)
        except ValueError as exc:
            raise ValueError(
                f"cannot convert passed value {value!r} to int"
            ) from exc

    def get_schema(self) -> Dict[str, Any]:
        # JSON-schema "integer" with 64-bit range, matching the Go
        # implementation's int64 property.
        return {"type": "integer", "format": "int64"}


class _FloatType(_BasicType):
    python_type = float

    def convert(self, value: str) -> float:
        if value == "":
            return 0.0
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(
                f"cannot convert passed value {value!r} to float"
            ) from exc

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "number", "format": "float"}


class _BytesType(_BasicType):
    """Bytes/bytearray — handled as base64-free raw strings.

    Fabric sends bytes as raw UTF-8 strings; we mirror that behaviour here.
    The Go implementation uses ``[]byte(param)`` which is a byte-for-byte
    cast of the UTF-8 bytes.
    """

    python_type = bytes

    def convert(self, value: str) -> bytes:
        return value.encode("utf-8")

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "string", "format": "byte"}


class _InterfaceType(_BasicType):
    """``typing.Any`` / untyped parameter — accept the raw string."""

    python_type = object

    def convert(self, value: str) -> str:
        return value

    def get_schema(self) -> Dict[str, Any]:
        return {}


# Order matters: when several Python types share the same identity (e.g. bool
# is a subclass of int), we need to check the more specific one first.
BasicTypes: Dict[TypeT, _BasicType] = {
    str: _StringType(),
    bool: _BoolType(),
    int: _IntType(),
    float: _FloatType(),
    bytes: _BytesType(),
    bytearray: _BytesType(),
    object: _InterfaceType(),
}

# Sentinel values mirroring Go's ``types.ErrorType`` and ``types.TimeType``.
ErrorType: TypeT = type("ErrorType", (), {"__doc__": "Sentinel for the Go-style error return type"})
TimeType: TypeT = _dt.datetime


def is_bytes(t: TypeT) -> bool:
    """Return ``True`` if *t* is a bytes/bytearray type.

    Mirrors ``types.IsBytes`` from the Go implementation.
    """
    return t in (bytes, bytearray)


def basic_type_for(t: TypeT) -> Optional[_BasicType]:
    """Return the basic-type adapter for *t*, or ``None``.

    Handles the ``bool`` is-a-subclass-of-``int`` gotcha by checking bool
    before int.
    """
    return BasicTypes.get(t)


__all__ = [
    "BasicTypes",
    "ErrorType",
    "TimeType",
    "is_bytes",
    "basic_type_for",
]
