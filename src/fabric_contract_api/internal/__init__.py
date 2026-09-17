# SPDX-License-Identifier: Apache-2.0
"""Internal package for :mod:`fabric_contract_api`.

This package mirrors Go's ``internal/`` directory and contains the building
blocks used by :mod:`fabric_contract_api.contractapi`.

To avoid circular imports we intentionally do **not** eagerly re-export the
sub-modules here — they are imported lazily by the modules that need them.
"""

# Sub-modules are imported on demand:
#   from .internal.types import BasicTypes, ErrorType, TimeType, is_bytes
#   from .internal.utils import slice_as_comma_sentence, string_in_slice, validate_errors_to_string
#   from .internal.contract_function import CallType, ContractFunction
#   from .internal.transaction_handler import TransactionHandler, TransactionHandlerType, new_transaction_handler
#   from .internal.types_handler import type_is_valid, type_matches_interface, list_basic_types
