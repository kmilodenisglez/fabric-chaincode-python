# SPDX-License-Identifier: Apache-2.0
"""JSON-schema utilities for contract metadata.

This is the Python equivalent of Go's ``metadata/schema.go``.  It walks a
Python type annotation (or ``typing`` alias) and produces a JSON-schema
fragment suitable for embedding into the chaincode metadata.

For complex types (dataclasses, plain classes, lists, dicts) the schema is
either inlined (for ``list``/``dict`` of basic types) or stored as a
component reference (``{"$ref": "#/components/schemas/ClassName"}``) so that
the schema can be reused across transactions and avoid infinite recursion
for self-referential structs.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import typing as _t
from typing import Any, Dict, List, Optional, Tuple, Type

from .metadata import ComponentMetadata
from ..internal.types import BasicTypes, is_bytes
from ..internal.types_handler import _strip_optional


def get_schema(field_type: Any, components: ComponentMetadata) -> Dict[str, Any]:
    """Return the JSON-schema fragment for *field_type*.

    Args:
        field_type: a Python type or ``typing`` alias.
        components: the mutable component-metadata registry.  Structs are
            added to this registry and the returned schema is a ``$ref``
            pointing to it.
    """
    return _get_schema(field_type, components, nested=False)


def _get_schema(field_type: Any, components: ComponentMetadata,
                nested: bool) -> Dict[str, Any]:
    field_type = _strip_optional(field_type)

    # bytes / bytearray -> {"type": "string", "format": "byte"}
    if is_bytes(field_type):
        return {"type": "string", "format": "byte"}

    # typing.Any / object -> empty schema (matches anything)
    if field_type is _t.Any or field_type is object:
        return {}

    # datetime / date -> date-time format
    if field_type is _dt.datetime or field_type is _dt.date:
        return {"type": "string", "format": "date-time"}

    # Basic scalar types
    if field_type in BasicTypes:
        return BasicTypes[field_type].get_schema()

    origin = _t.get_origin(field_type)
    args = _t.get_args(field_type)

    if origin is list or origin is _t.List:
        return _build_list_schema(args, components, nested)
    if origin is tuple or origin is _t.Tuple:
        return _build_list_schema(args, components, nested)
    if origin is dict or origin is _t.Dict:
        return _build_dict_schema(args, components, nested)

    if isinstance(field_type, type) and (
            dataclasses.is_dataclass(field_type) or hasattr(field_type, "__dict__")):
        return _build_struct_schema(field_type, components, nested)

    raise ValueError(f"{field_type!r} was not a valid type")


def _build_list_schema(args: Tuple[Any, ...], components: ComponentMetadata,
                       nested: bool) -> Dict[str, Any]:
    if not args:
        return {"type": "array", "items": {}}
    item_schema = _get_schema(args[0], components, nested)
    return {"type": "array", "items": item_schema}


def _build_dict_schema(args: Tuple[Any, ...], components: ComponentMetadata,
                       nested: bool) -> Dict[str, Any]:
    if not args or len(args) != 2:
        return {"type": "object"}
    value_schema = _get_schema(args[1], components, nested)
    return {
        "type": "object",
        "additionalProperties": value_schema,
    }


def _build_struct_schema(obj_type: Type[Any], components: ComponentMetadata,
                         nested: bool) -> Dict[str, Any]:
    """Build (or reference) the schema for a struct type."""
    err = _add_component_if_not_exists(obj_type, components)
    if err is not None:
        raise err
    ref_path = "" if nested else "#/components/schemas/"
    return {"$ref": f"{ref_path}{obj_type.__name__}"}


def _add_component_if_not_exists(obj_type: Type[Any],
                                 components: ComponentMetadata) -> Optional[Exception]:
    """Register *obj_type* in *components* if not already present.

    Returns ``None`` on success, or an ``Exception`` describing the failure.
    """
    name = obj_type.__name__
    if name in components.schemas:
        return None

    schema = {
        "$id": name,
        "required": [],
        "properties": {},
        "additionalProperties": False,
    }
    components.schemas[name] = schema  # reserve slot for cyclic refs

    try:
        if dataclasses.is_dataclass(obj_type):
            # Resolve PEP 563 string annotations to actual types so that
            # ``from __future__ import annotations`` works correctly.
            try:
                resolved = _t.get_type_hints(obj_type)
            except Exception:
                resolved = {}
            for field in dataclasses.fields(obj_type):
                field_type = resolved.get(field.name, field.type)
                err = _get_field_dataclass(field, field_type, schema, components)
                if err:
                    del components.schemas[name]
                    return err
        else:
            # Plain class — use __init__ type hints as field descriptors.
            try:
                hints = _t.get_type_hints(obj_type.__init__)
            except Exception:
                hints = {}
            for fname, ftype in hints.items():
                if fname in ("self", "return"):
                    continue
                err = _get_field_plain(fname, ftype, schema, components)
                if err:
                    del components.schemas[name]
                    return err
    except Exception as exc:  # pragma: no cover - defensive
        del components.schemas[name]
        return exc

    components.schemas[name] = schema
    return None


def _resolve_field_name(field_name: str, metadata_tag: str, json_tag: str) -> Tuple[str, bool, bool]:
    """Resolve the public field name, required flag and "skip" flag.

    Mirrors Go's ``getField`` parsing logic for struct tags:
    * If the ``metadata`` tag is ``-`` the field is skipped.
    * If the ``metadata`` tag is ``name[,optional]`` the field is renamed and
      may be marked optional.
    * If the ``metadata`` tag is empty the ``json`` tag (without ``,omitempty``
      suffix) is used, falling back to the Python attribute name.
    """
    if metadata_tag == "-":
        return "", False, True

    name = metadata_tag
    required = True
    if "," in name:
        parts = name.split(",")
        name = parts[0]
        for extra in parts[1:]:
            if extra.strip() == "optional":
                required = False

    if name == "":
        # Fall back to the json tag, if any.
        if json_tag:
            if "," in json_tag:
                name = json_tag.split(",")[0]
            else:
                name = json_tag

    if name == "" or name == "-":
        name = field_name

    return name, required, False


def _get_field_dataclass(field: Any, field_type: Any, schema: Dict[str, Any],
                         components: ComponentMetadata) -> Optional[Exception]:
    """Populate *schema* from a single dataclass field."""
    metadata_tag = ""
    if isinstance(field.metadata, dict):
        metadata_tag = field.metadata.get("metadata", "")
    json_tag = ""
    # dataclass fields don't have native json tags — fall back to the
    # field.name.  The user can still pass `metadata={"metadata": "myName"}`
    # to rename it.
    name, required, skip = _resolve_field_name(field.name, metadata_tag, json_tag)
    if skip:
        return None

    try:
        prop_schema = _get_schema(field_type, components, nested=True)
    except Exception as exc:
        return exc

    if required:
        schema["required"].append(name)
    schema["properties"][name] = prop_schema
    return None


def _get_field_plain(field_name: str, field_type: Any,
                     schema: Dict[str, Any],
                     components: ComponentMetadata) -> Optional[Exception]:
    """Populate *schema* from a single plain-class ``__init__`` parameter."""
    # No native "metadata"/"json" tags for plain classes; use the raw name.
    name = field_name
    required = True

    try:
        prop_schema = _get_schema(field_type, components, nested=True)
    except Exception as exc:
        return exc

    if required:
        schema["required"].append(name)
    schema["properties"][name] = prop_schema
    return None


__all__ = ["get_schema"]
