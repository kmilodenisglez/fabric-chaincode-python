# SPDX-License-Identifier: Apache-2.0
"""JSON transaction serializer.

This is the Python equivalent of Go's ``serializer/json_transaction_serializer.go``.
It converts string arguments to typed Python values using the standard
:mod:`json` library, validates them against their JSON-schema (when
:mod:`jsonschema` is available) and serialises the return value back into a
JSON string.

The serializer supports:

* basic scalars (``str``, ``bool``, ``int``, ``float``)
* ``bytes`` / ``bytearray`` (treated as raw byte strings)
* :class:`datetime.datetime` and :class:`datetime.date` (RFC 3339)
* ``list`` / ``typing.List[T]``
* ``dict`` / ``typing.Dict[str, V]``
* dataclasses and plain classes (serialised as JSON objects)
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import typing as _t
from typing import Any, Optional, Tuple

from ..internal import types as _types
from ..metadata import ComponentMetadata, ParameterMetadata, ReturnMetadata
from .transaction_serializer import TransactionSerializer


class JSONSerializer(TransactionSerializer):
    """Default JSON transaction serializer.

    Mirrors Go's ``JSONSerializer``.
    """

    # ------------------------------------------------------------------
    # FromString
    # ------------------------------------------------------------------

    def from_string(self, value: str, field_type: Any,
                    param_metadata: Optional[ParameterMetadata],
                    components: Optional[ComponentMetadata]) -> Tuple[Any, Optional[Exception]]:
        try:
            converted = self._convert_arg(field_type, value)
        except Exception as exc:
            return None, exc

        if param_metadata is not None and param_metadata.compiled_schema is not None:
            err = self._validate_against_schema(
                param_metadata.name, field_type, value,
                converted, param_metadata.compiled_schema,
            )
            if err is not None:
                return None, err

        return converted, None

    # ------------------------------------------------------------------
    # ToString
    # ------------------------------------------------------------------

    def to_string(self, result: Any, result_type: Any,
                  returns: Optional[ReturnMetadata],
                  components: Optional[ComponentMetadata]) -> Tuple[str, Optional[Exception]]:
        if result is None:
            return "", None

        # Special-case known types first.
        if result_type is _dt.datetime or isinstance(result, _dt.datetime):
            s = result.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if isinstance(result, _dt.datetime) else str(result)
            if returns is not None and returns.compiled_schema is not None:
                err = self._validate_against_schema(
                    "return", result_type, s, result, returns.compiled_schema
                )
                if err is not None:
                    return "", err
            return s, None

        if _types.is_bytes(result_type) or isinstance(result, (bytes, bytearray)):
            try:
                s = result.decode("utf-8") if isinstance(result, (bytes, bytearray)) else str(result)
            except Exception:
                s = str(result)
            if returns is not None and returns.compiled_schema is not None:
                err = self._validate_against_schema(
                    "return", result_type, s, s, returns.compiled_schema
                )
                if err is not None:
                    return "", err
            return s, None

        if self._is_marshalling_type(result_type) or self._is_marshalling_type(type(result)):
            try:
                s = self._to_json_string(result)
            except Exception as exc:
                return "", exc
            if returns is not None and returns.compiled_schema is not None:
                err = self._validate_against_schema(
                    "return", result_type, s, s, returns.compiled_schema
                )
                if err is not None:
                    return "", err
            return s, None

        # Basic scalar
        s = str(result)
        if returns is not None and returns.compiled_schema is not None:
            err = self._validate_against_schema(
                "return", result_type, s, result, returns.compiled_schema
            )
            if err is not None:
                return "", err
        return s, None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _convert_arg(self, field_type: Any, param_value: str) -> Any:
        field_type = _strip_optional(field_type)

        if field_type is _dt.datetime or field_type is _dt.date:
            try:
                return _dt.datetime.fromisoformat(param_value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(
                    f"value {param_value!r} was not passed in expected format "
                    f"{getattr(field_type, '__name__', field_type)}"
                ) from exc

        if _types.is_bytes(field_type):
            return param_value.encode("utf-8")

        origin = _t.get_origin(field_type)
        if origin in (list, _t.List, tuple, _t.Tuple, dict, _t.Dict):
            try:
                return json.loads(param_value) if param_value != "" else self._empty_for(field_type)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"value {param_value!r} was not passed in expected format "
                    f"{getattr(field_type, '__name__', str(field_type))}"
                ) from exc

        # User-defined classes (dataclasses or plain classes) are JSON-decoded.
        if isinstance(field_type, type) and field_type not in _types.BasicTypes and (
                dataclasses.is_dataclass(field_type) or _is_user_class(field_type)):
            try:
                obj = json.loads(param_value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"value {param_value!r} was not passed in expected format "
                    f"{field_type.__name__}"
                ) from exc
            if isinstance(obj, dict):
                try:
                    if dataclasses.is_dataclass(field_type):
                        return _dataclass_from_dict(field_type, obj)
                    return _plain_class_from_dict(field_type, obj)
                except Exception as exc:
                    raise ValueError(
                        f"value {param_value!r} was not passed in expected format "
                        f"{field_type.__name__}: {exc}"
                    ) from exc
            return obj

        if field_type is _t.Any or field_type is object:
            return param_value

        # Basic scalar
        adapter = _types.BasicTypes.get(field_type)
        if adapter is None:
            raise ValueError(
                f"conversion error. type {field_type!r} is not supported"
            )
        return adapter.convert(param_value)

    def _empty_for(self, field_type: Any) -> Any:
        origin = _t.get_origin(field_type)
        if origin in (list, _t.List, tuple, _t.Tuple):
            return []
        if origin in (dict, _t.Dict):
            return {}
        return None

    def _is_marshalling_type(self, tp: Any) -> bool:
        if _types.is_bytes(tp):
            return False
        # Basic scalars (str/int/bool/float) are not "marshalling" types —
        # they get passed straight through as plain strings.
        if tp in _types.BasicTypes:
            return False
        origin = _t.get_origin(tp)
        if origin in (list, _t.List, tuple, _t.Tuple, dict, _t.Dict):
            return True
        if isinstance(tp, type):
            if dataclasses.is_dataclass(tp):
                return True
            # Only user-defined classes are "marshalling" types — builtins
            # such as ``str``/``int`` satisfy ``hasattr(tp, "__dict__")``
            # but must not go through JSON marshalling.
            return _is_user_class(tp)
        return False

    def _to_json_string(self, value: Any) -> str:
        if dataclasses.is_dataclass(value):
            return json.dumps(_dataclass_to_dict(value), default=_json_default)
        if isinstance(value, (list, tuple)):
            return json.dumps(list(value), default=_json_default)
        if isinstance(value, dict):
            return json.dumps(value, default=_json_default)
        if hasattr(value, "__dict__"):
            d = {k: v for k, v in vars(value).items() if not k.startswith("_") and not callable(v)}
            return json.dumps(d, default=_json_default)
        return json.dumps(value, default=_json_default)

    def _validate_against_schema(self, prop_name: str, typ: Any,
                                  string_value: str, obj: Any,
                                  compiled_schema: Any) -> Optional[Exception]:
        try:
            import jsonschema  # type: ignore
        except Exception:
            return None

        # Build the document to validate.  Complex types (lists, dicts,
        # structs) are validated against their JSON-decoded form so that
        # $ref to #/components/schemas/... resolves correctly.
        to_validate: Any
        if isinstance(obj, _dt.datetime):
            to_validate = {prop_name: string_value}
        elif _t.get_origin(typ) in (list, _t.List, tuple, _t.Tuple, dict, _t.Dict):
            try:
                to_validate = {prop_name: json.loads(string_value)}
            except json.JSONDecodeError as exc:
                return exc
        elif isinstance(typ, type) and typ not in _types.BasicTypes and (
                dataclasses.is_dataclass(typ) or _is_user_class(typ)):
            try:
                to_validate = {prop_name: json.loads(string_value)}
            except json.JSONDecodeError as exc:
                return exc
        else:
            to_validate = {prop_name: obj}

        # ``compiled_schema`` is a jsonschema Validator instance.
        try:
            if isinstance(compiled_schema, dict) and "raw" in compiled_schema:
                # jsonschema wasn't available at compile time — skip
                return None
            errors = list(compiled_schema.iter_errors(to_validate))
        except Exception as exc:
            return exc

        if errors:
            from ..internal.utils import validate_errors_to_string
            msgs = [f"{err.message} at {list(err.absolute_path)}" for err in errors]
            return ValueError(
                "value did not match schema:\n" + validate_errors_to_string(msgs)
            )
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_BASIC_TYPE_NAMES = {"str", "int", "float", "bool", "bytes", "bytearray",
                      "list", "dict", "set", "tuple", "object", "NoneType",
                      "type"}


def _is_user_class(tp: Any) -> bool:
    """Return ``True`` if *tp* is a user-defined class (not a builtin).

    Used to avoid the trap where ``str``/``int`` etc. satisfy
    ``hasattr(tp, "__dict__")`` because they're classes with class-level
    attributes.
    """
    if not isinstance(tp, type):
        return False
    if tp.__module__ in ("builtins", "typing", "dataclasses"):
        return False
    return tp.__name__ not in _BASIC_TYPE_NAMES


def _strip_optional(tp: Any) -> Any:
    origin = _t.get_origin(tp)
    if origin is _t.Union:
        args = [a for a in _t.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _json_default(obj: Any) -> Any:
    if isinstance(obj, _dt.datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(obj, _dt.date):
        return obj.isoformat()
    if isinstance(obj, (bytes, bytearray)):
        return obj.decode("utf-8", errors="replace")
    if dataclasses.is_dataclass(obj):
        return _dataclass_to_dict(obj)
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_") and not callable(v)}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


def _dataclass_to_dict(obj: Any) -> Any:
    out: dict = {}
    for f in dataclasses.fields(obj):
        value = getattr(obj, f.name)
        out[f.name] = value
    return out


def _dataclass_from_dict(cls: type, d: dict) -> Any:
    kwargs = {}
    hints = _t.get_type_hints(cls.__init__)
    for f in dataclasses.fields(cls):
        if f.name in d:
            kwargs[f.name] = d[f.name]
        elif f.default is not dataclasses.MISSING:
            continue
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            continue
    return cls(**kwargs)


def _plain_class_from_dict(cls: type, d: dict) -> Any:
    """Instantiate *cls* from a dict, mapping keys to ``__init__`` parameters."""
    import inspect

    sig = inspect.signature(cls.__init__)
    params = sig.parameters
    kwargs: dict = {}
    for pname, param in params.items():
        if pname == "self":
            continue
        if pname in d:
            kwargs[pname] = d[pname]
        elif param.default is not inspect.Parameter.empty:
            continue
        else:
            # If the parameter is required but missing, leave it out and let
            # the constructor raise a meaningful error.
            continue
    return cls(**kwargs)


__all__ = ["JSONSerializer"]
