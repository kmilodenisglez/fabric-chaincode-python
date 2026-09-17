# SPDX-License-Identifier: Apache-2.0
"""Contract API package for :mod:`fabric_contract_api`.

Mirrors Go's ``contractapi`` package.  Provides the high-level building
blocks for declaring and running contracts:

* :class:`Contract` — base class for application contracts.
* :class:`ContractChaincode` — chaincode adapter that dispatches to
  registered contracts.
* :class:`TransactionContext` and :class:`TransactionContextInterface` —
  per-transaction context passed to contract functions.
* :class:`SystemContract` — built-in contract that exposes chaincode
  metadata.
"""

from .contract import (  # noqa: F401
    Contract,
    ContractInterface,
    EvaluationContractInterface,
    IgnoreContractInterface,
)
from .contract_chaincode import ContractChaincode  # noqa: F401
from .system_contract import SystemContract, SystemContractName  # noqa: F401
from .transaction_context import (  # noqa: F401
    ClientIdentity,
    SettableTransactionContextInterface,
    TransactionContext,
    TransactionContextInterface,
)
