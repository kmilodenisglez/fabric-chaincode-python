# SPDX-License-Identifier: Apache-2.0
"""Contract chaincode metadata dataclasses and helpers.

This is the Python equivalent of Go's ``metadata/metadata.go``.  It defines
dataclasses for the various metadata pieces (info, contract, transaction,
parameter, return, components, contract-chaincode) and provides:

* :func:`read_metadata_file` — read a user-supplied ``metadata.json`` file
  from one of the well-known metadata folders.
* :func:`validate_against_schema` — validate the produced metadata against
  the JSON schema shipped in :mod:`fabric_contract_api.metadata.schema`.
* :meth:`ContractChaincodeMetadata.append` — merge two metadata trees.
* :meth:`ContractChaincodeMetadata.compile_schemas` — pre-compile parameter
  and return schemas into ``CompiledSchema`` validators so that they can be
  used by the JSON serializer at call time.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:  # jsonschema is optional — the JSON serializer degrades gracefully.
    import jsonschema  # type: ignore
    _HAS_JSONSCHEMA = True
except Exception:  # pragma: no cover - optional dep
    _HAS_JSONSCHEMA = False


METADATA_FOLDER = "META-INF"
METADATA_FOLDER_SECONDARY = "contract-metadata"
METADATA_FILE = "metadata.json"

_SCHEMA_JSON_PATH = os.path.join(os.path.dirname(__file__), "schema", "schema.json")


def get_json_schema() -> bytes:
    """Return the raw bytes of the JSON schema shipped with this package."""
    with open(_SCHEMA_JSON_PATH, "rb") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ParameterMetadata:
    """Metadata describing a single parameter of a transaction function."""

    description: str = ""
    name: str = ""
    schema: Optional[Dict[str, Any]] = None
    compiled_schema: Any = None  # an opaque, serializer-specific validator

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name}
        if self.description:
            d["description"] = self.description
        if self.schema is not None:
            d["schema"] = self.schema
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ParameterMetadata":
        return cls(
            description=d.get("description", "") or "",
            name=d.get("name", "") or "",
            schema=d.get("schema"),
        )


@dataclass
class ReturnMetadata:
    """Metadata describing the return value of a transaction function."""

    schema: Optional[Dict[str, Any]] = None
    compiled_schema: Any = None


@dataclass
class TransactionMetadata:
    """Metadata describing a single transaction function."""

    name: str = ""
    tag: List[str] = field(default_factory=list)
    parameters: List[ParameterMetadata] = field(default_factory=list)
    returns: ReturnMetadata = field(default_factory=ReturnMetadata)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name}
        if self.tag:
            d["tag"] = list(self.tag)
        if self.parameters:
            d["parameters"] = [p.to_dict() for p in self.parameters]
        if self.returns.schema is not None:
            d["returns"] = self.returns.schema
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TransactionMetadata":
        params = [ParameterMetadata.from_dict(p) for p in (d.get("parameters") or [])]
        returns = ReturnMetadata(schema=d.get("returns"))
        return cls(
            name=d.get("name", "") or "",
            tag=list(d.get("tag") or []),
            parameters=params,
            returns=returns,
        )


@dataclass
class ContactMetadata:
    name: str = ""
    url: str = ""
    email: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.name:
            d["name"] = self.name
        if self.url:
            d["url"] = self.url
        if self.email:
            d["email"] = self.email
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContactMetadata":
        return cls(
            name=d.get("name", "") or "",
            url=d.get("url", "") or "",
            email=d.get("email", "") or "",
        )


@dataclass
class LicenseMetadata:
    name: str = ""
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.name:
            d["name"] = self.name
        if self.url:
            d["url"] = self.url
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LicenseMetadata":
        return cls(
            name=d.get("name", "") or "",
            url=d.get("url", "") or "",
        )


@dataclass
class InfoMetadata:
    """Top-level info block (title, version, contact, license, ...)."""

    description: str = ""
    title: str = ""
    contact: Optional[ContactMetadata] = None
    license: Optional[LicenseMetadata] = None
    version: str = ""
    terms_of_service: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.description:
            d["description"] = self.description
        if self.title:
            d["title"] = self.title
        if self.contact:
            d["contact"] = self.contact.to_dict()
        if self.license:
            d["license"] = self.license.to_dict()
        if self.version:
            d["version"] = self.version
        if self.terms_of_service:
            d["termsOfService"] = self.terms_of_service
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "InfoMetadata":
        return cls(
            description=d.get("description", "") or "",
            title=d.get("title", "") or "",
            contact=ContactMetadata.from_dict(d["contact"]) if d.get("contact") else None,
            license=LicenseMetadata.from_dict(d["license"]) if d.get("license") else None,
            version=d.get("version", "") or "",
            terms_of_service=d.get("termsOfService", "") or "",
        )


@dataclass
class ContractMetadata:
    """Metadata describing a single contract."""

    info: Optional[InfoMetadata] = None
    name: str = ""
    transactions: List[TransactionMetadata] = field(default_factory=list)
    default: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "transactions": [t.to_dict() for t in self.transactions],
            "default": self.default,
        }
        if self.info:
            d["info"] = self.info.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContractMetadata":
        return cls(
            info=InfoMetadata.from_dict(d["info"]) if d.get("info") else None,
            name=d.get("name", "") or "",
            transactions=[
                TransactionMetadata.from_dict(t) for t in (d.get("transactions") or [])
            ],
            default=bool(d.get("default", False)),
        )


@dataclass
class ObjectMetadata:
    """Description of a single component (struct) used by the contract API."""

    id: str = ""
    properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    additional_properties: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "$id": self.id,
            "properties": dict(self.properties),
            "required": list(self.required),
            "additionalProperties": self.additional_properties,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ObjectMetadata":
        return cls(
            id=d.get("$id", "") or "",
            properties=dict(d.get("properties") or {}),
            required=list(d.get("required") or []),
            additional_properties=bool(d.get("additionalProperties", False)),
        )


@dataclass
class ComponentMetadata:
    """Stores map of schemas of all components."""

    schemas: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        if not self.schemas:
            return {}
        return {"schemas": dict(self.schemas)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ComponentMetadata":
        return cls(schemas=dict(d.get("schemas") or {}))


@dataclass
class ContractChaincodeMetadata:
    """Top-level metadata describing a chaincode built from contracts."""

    info: Optional[InfoMetadata] = None
    contracts: Dict[str, ContractMetadata] = field(default_factory=dict)
    components: ComponentMetadata = field(default_factory=ComponentMetadata)

    # -- (de)serialization ---------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"contracts": {}}
        if self.info:
            d["info"] = self.info.to_dict()
        d["contracts"] = {k: v.to_dict() for k, v in self.contracts.items()}
        components_dict = self.components.to_dict()
        if components_dict:
            d["components"] = components_dict
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContractChaincodeMetadata":
        return cls(
            info=InfoMetadata.from_dict(d["info"]) if d.get("info") else None,
            contracts={
                k: ContractMetadata.from_dict(v)
                for k, v in (d.get("contracts") or {}).items()
            },
            components=ComponentMetadata.from_dict(d.get("components") or {}),
        )

    # -- merging -------------------------------------------------------------

    def append(self, source: "ContractChaincodeMetadata") -> None:
        """Merge *source* into this metadata.

        Source values only override target values that are not yet set.
        Mirrors ``ContractChaincodeMetadata.Append`` from the Go code.
        """
        if self.info is None:
            self.info = source.info

        if not self.contracts:
            for key, value in source.contracts.items():
                self.contracts[key] = value

        if not self.components.schemas:
            self.components = source.components

    # -- schema compilation --------------------------------------------------

    def compile_schemas(self) -> Optional[Exception]:
        """Pre-compile every parameter and return schema.

        The compiled schema is stored on the metadata object so the JSON
        serializer can re-use it without re-parsing on every call.
        """
        for contract_name, contract in self.contracts.items():
            for tx in contract.transactions:
                for i, param in enumerate(tx.parameters):
                    compiled, err = _compile_schema(param.name, param.schema, self.components)
                    if err is not None:
                        return err
                    param.compiled_schema = compiled
                    tx.parameters[i] = param

                if tx.returns.schema is not None:
                    compiled, err = _compile_schema("return", tx.returns.schema, self.components)
                    if err is not None:
                        return err
                    tx.returns.compiled_schema = compiled
        return None


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _compile_schema(prop_name: str, schema: Optional[Dict[str, Any]],
                    components: ComponentMetadata):
    """Combine a per-parameter schema with the components map.

    Returns ``(compiled, None)`` on success or ``(None, Exception)`` on
    failure.  The compiled value is opaque to the metadata layer — it is
    passed straight through to the serializer, which interprets it.
    """
    if schema is None:
        return None, None

    # The JSON serializer uses ``jsonschema`` validators when available.
    # The combined schema wraps the parameter schema under a "properties"
    # key so the validator can check ``{"paramName": value}``.
    combined = {
        "components": components.to_dict() or {},
        "properties": {prop_name: schema},
    }
    if not _HAS_JSONSCHEMA:
        # No validator available — return the raw combined dict so the
        # serializer can still attempt a manual check.
        return {"raw": combined, "schema": schema}, None

    try:
        # We construct a validator whose root schema is the combined dict
        # so that $ref references to #/components/schemas/... resolve.
        validator_cls = jsonschema.validators.validator_for(combined)
        validator_cls.check_schema(combined)
        return validator_cls(combined), None
    except Exception as exc:
        return None, exc


def read_metadata_file() -> "ContractChaincodeMetadata":
    """Read the metadata file from one of the known folders.

    Raises :class:`FileNotFoundError` when the file cannot be found.
    Mirrors Go's ``ReadMetadataFile``.
    """
    cwd = os.getcwd()
    primary_path = os.path.join(cwd, METADATA_FOLDER, METADATA_FILE)
    secondary_path = os.path.join(cwd, METADATA_FOLDER_SECONDARY, METADATA_FILE)

    for path in (primary_path, secondary_path):
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                data = fh.read()
            return ContractChaincodeMetadata.from_dict(json.loads(data))

    raise FileNotFoundError(
        f"metadata file not found at {primary_path} or {secondary_path}"
    )


def validate_against_schema(metadata: ContractChaincodeMetadata) -> Optional[Exception]:
    """Validate *metadata* against the JSON schema shipped with this package.

    Returns ``None`` if the metadata is valid, otherwise an ``Exception``
    describing the failure.
    """
    if not _HAS_JSONSCHEMA:
        # Without jsonschema we cannot validate.  Be permissive: the metadata
        # produced by reflection is always valid; only user-supplied metadata
        # files would slip through here.
        return None

    raw = json.loads(metadata.to_json())
    schema = json.loads(get_json_schema())
    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
        errors = list(validator.iter_errors(raw))
    except Exception as exc:
        return exc

    if errors:
        from ..internal.utils import validate_errors_to_string
        msgs = [f"{err.message} at {list(err.absolute_path)}" for err in errors]
        return ValueError(
            "cannot use metadata. Metadata did not match schema:\n"
            + validate_errors_to_string(msgs)
        )
    return None


__all__ = [
    "ComponentMetadata",
    "ContactMetadata",
    "ContractChaincodeMetadata",
    "ContractMetadata",
    "InfoMetadata",
    "LicenseMetadata",
    "ObjectMetadata",
    "ParameterMetadata",
    "ReturnMetadata",
    "TransactionMetadata",
    "get_json_schema",
    "read_metadata_file",
    "validate_against_schema",
]
