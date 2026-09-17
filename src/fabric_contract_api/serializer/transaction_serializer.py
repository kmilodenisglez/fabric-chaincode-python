# SPDX-License-Identifier: Apache-2.0
"""Transaction serializers for :mod:`fabric_contract_api`.

A transaction serializer is responsible for converting the string arguments
that arrive in a Fabric transaction payload into the typed Python values
expected by a contract function, and for converting the value returned by
the contract function back into a string that can be sent back to the peer.
"""

from __future__ import annotations

import abc
from typing import Any, Optional, Tuple, Type

from ..metadata import ComponentMetadata, ParameterMetadata, ReturnMetadata


class TransactionSerializer(abc.ABC):
    """Abstract base for transaction serializers.

    Mirrors Go's ``serializer.TransactionSerializer`` interface.
    """

    @abc.abstractmethod
    def from_string(self, value: str, field_type: Any,
                    param_metadata: Optional[ParameterMetadata],
                    components: Optional[ComponentMetadata]) -> Tuple[Any, Optional[Exception]]:
        """Convert *value* into a Python value of *field_type*.

        Returns ``(converted_value, None)`` on success or
        ``(None, Exception)`` on failure.
        """

    @abc.abstractmethod
    def to_string(self, result: Any, result_type: Any,
                  returns: Optional[ReturnMetadata],
                  components: Optional[ComponentMetadata]) -> Tuple[str, Optional[Exception]]:
        """Convert *result* back into a string representation.

        Returns ``(string, None)`` on success or ``("", Exception)`` on
        failure.
        """


__all__ = ["TransactionSerializer"]
