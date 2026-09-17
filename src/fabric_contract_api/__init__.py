# SPDX-License-Identifier: Apache-2.0
"""Hyperledger Fabric Contract API for Python.

This package provides a high-level, contract-oriented programming model on
top of the low-level :mod:`fabric_shim` chaincode shim.  It is the Python
equivalent of Hyperledger's ``fabric-contract-api-go``.

Public surface (mirrors the Go layout)::

    fabric_contract_api.contractapi            # Contract, ContractChaincode, ...
    fabric_contract_api.serializer            # TransactionSerializer, JSONSerializer
    fabric_contract_api.metadata              # Metadata types & schema helpers
    fabric_contract_api.internal              # Introspection & type validation helpers

The most useful imports for application developers are::

    from fabric_contract_api.contractapi import Contract, ContractChaincode
    from fabric_contract_api.contractapi import TransactionContext, TransactionContextInterface
"""

from .contractapi import (  # noqa: F401  (re-exported for convenience)
    Contract,
    ContractChaincode,
    ContractInterface,
    EvaluationContractInterface,
    IgnoreContractInterface,
    SystemContract,
    SystemContractName,
    TransactionContext,
    TransactionContextInterface,
    SettableTransactionContextInterface,
)
from .serializer import (  # noqa: F401
    TransactionSerializer,
    JSONSerializer,
)

__all__ = [
    "Contract",
    "ContractChaincode",
    "ContractInterface",
    "EvaluationContractInterface",
    "IgnoreContractInterface",
    "SystemContract",
    "SystemContractName",
    "TransactionContext",
    "TransactionContextInterface",
    "SettableTransactionContextInterface",
    "TransactionSerializer",
    "JSONSerializer",
]
