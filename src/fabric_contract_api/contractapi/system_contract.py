# SPDX-License-Identifier: Apache-2.0
"""System contract added to every chaincode.

This is the Python equivalent of Go's ``contractapi/system_contract.go``.
The system contract exposes a single ``GetMetadata`` transaction that
returns the JSON-formatted metadata of the chaincode it belongs to.
"""

from __future__ import annotations

from typing import List

from .contract import Contract

#: The well-known name of the system contract.
SystemContractName = "org.hyperledger.fabric"


class SystemContract(Contract):
    """Built-in contract that exposes chaincode metadata."""

    Name: str = SystemContractName

    def __init__(self) -> None:
        super().__init__()
        self._metadata: str = ""

    def _set_metadata(self, metadata: str) -> None:
        """Inject the metadata JSON into the system contract.

        Called by :class:`ContractChaincode` once the metadata has been
        compiled from the registered contracts.
        """
        self._metadata = metadata

    def get_metadata(self) -> str:
        """Return the JSON metadata of the chaincode this contract belongs to."""
        return self._metadata

    def get_evaluate_transactions(self) -> List[str]:
        """Return the names of the transactions that should be evaluated."""
        return ["get_metadata"]


__all__ = ["SystemContract", "SystemContractName"]
