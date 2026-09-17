# SPDX-License-Identifier: Apache-2.0
"""Contract base classes and interfaces.

This is the Python equivalent of Go's ``contractapi/contract.go``.  It
defines:

* :class:`ContractInterface` — the :class:`abc.ABC` every contract must
  implement.
* :class:`IgnoreContractInterface` — optional interface for contracts that
  want to mark certain public methods as not callable from the outside.
* :class:`EvaluationContractInterface` — optional interface that lets a
  contract declare which transactions are "evaluate" (i.e. read-only queries).
* :class:`Contract` — a concrete base class with sensible defaults that
  application contracts can subclass (or embed) to quickly satisfy the
  interfaces.
"""

from __future__ import annotations

import abc
from typing import Any, List, Optional

from ..metadata import InfoMetadata
from .transaction_context import (
    SettableTransactionContextInterface,
    TransactionContext,
)


class ContractInterface(abc.ABC):
    """Interface that every contract must implement."""

    @abc.abstractmethod
    def get_info(self) -> InfoMetadata:
        """Return the info block used in the metadata."""

    @abc.abstractmethod
    def get_unknown_transaction(self) -> Optional[Any]:
        """Return the unknown-transaction callable, or ``None``."""

    @abc.abstractmethod
    def get_before_transaction(self) -> Optional[Any]:
        """Return the before-transaction callable, or ``None``."""

    @abc.abstractmethod
    def get_after_transaction(self) -> Optional[Any]:
        """Return the after-transaction callable, or ``None``."""

    @abc.abstractmethod
    def get_name(self) -> str:
        """Return the name of the contract."""

    @abc.abstractmethod
    def get_transaction_context_handler(self) -> SettableTransactionContextInterface:
        """Return the transaction-context class to use."""


class IgnoreContractInterface(abc.ABC):
    """Optional interface for marking methods as not-callable."""

    @abc.abstractmethod
    def get_ignored_functions(self) -> List[str]:
        """Return the list of method names that should be excluded."""


class EvaluationContractInterface(abc.ABC):
    """Optional interface for marking methods as evaluate (read-only)."""

    @abc.abstractmethod
    def get_evaluate_transactions(self) -> List[str]:
        """Return the list of method names tagged as evaluate."""


class Contract(ContractInterface):
    """Default contract base class.

    Subclass this to define your own contract.  You only need to override
    the methods that are interesting to you::

        class MyContract(Contract):
            Name = "MyContract"

            def my_transaction(self, ctx, key: str) -> str:
                ...

    The following attributes are set as plain instance/class attributes so
    they can be easily overridden:

    * :attr:`Name` — the contract name.
    * :attr:`Info` — a :class:`metadata.InfoMetadata` describing the contract.
    * :attr:`UnknownTransaction` — callable for unknown-transaction handling.
    * :attr:`BeforeTransaction` — callable invoked before each transaction.
    * :attr:`AfterTransaction` — callable invoked after each transaction.
    * :attr:`TransactionContextHandler` — the transaction-context class.
    """

    Name: str = ""
    Info: Optional[InfoMetadata] = None
    UnknownTransaction: Optional[Any] = None
    BeforeTransaction: Optional[Any] = None
    AfterTransaction: Optional[Any] = None
    TransactionContextHandler: Optional[type] = None

    def __init__(self) -> None:
        # Each Contract instance gets its own InfoMetadata so subclasses don't
        # accidentally share state via the class-level attribute.
        if self.Info is None:
            self.Info = InfoMetadata()

    def get_info(self) -> InfoMetadata:
        if self.Info is None:
            self.Info = InfoMetadata()
        return self.Info

    def get_unknown_transaction(self) -> Optional[Any]:
        return self.UnknownTransaction

    def get_before_transaction(self) -> Optional[Any]:
        return self.BeforeTransaction

    def get_after_transaction(self) -> Optional[Any]:
        return self.AfterTransaction

    def get_name(self) -> str:
        return self.Name

    def get_transaction_context_handler(self) -> SettableTransactionContextInterface:
        if self.TransactionContextHandler is None:
            return TransactionContext()
        handler = self.TransactionContextHandler
        if isinstance(handler, type):
            return handler()
        return handler


__all__ = [
    "Contract",
    "ContractInterface",
    "EvaluationContractInterface",
    "IgnoreContractInterface",
]
