# SPDX-License-Identifier: Apache-2.0
"""Metadata package for :mod:`fabric_contract_api`.

Mirrors Go's ``metadata`` package: dataclasses describing the contract
chaincode metadata, JSON-schema helpers, and the embedded schema used to
validate user-supplied metadata files.
"""

# Import the metadata dataclasses and helpers eagerly.  ``schema.py`` is
# imported lazily (via ``from .schema import get_schema``) by callers that
# actually need it to avoid a circular import with the ``internal`` package.
from .metadata import (  # noqa: F401
    ComponentMetadata,
    ContactMetadata,
    ContractChaincodeMetadata,
    ContractMetadata,
    InfoMetadata,
    LicenseMetadata,
    ObjectMetadata,
    ParameterMetadata,
    ReturnMetadata,
    TransactionMetadata,
    get_json_schema,
    read_metadata_file,
    validate_against_schema,
)


def get_schema(field_type, components):  # pragma: no cover - thin proxy
    """Lazy re-export of :func:`fabric_contract_api.metadata.schema.get_schema`."""
    from .schema import get_schema as _impl
    return _impl(field_type, components)
