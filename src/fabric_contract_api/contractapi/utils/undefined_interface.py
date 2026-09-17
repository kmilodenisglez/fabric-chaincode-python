# SPDX-License-Identifier: Apache-2.0
"""Sentinel type for the "no return value" case in after-transactions.

Mirrors Go's ``contractapi/utils/undefined_interface.go``.  When an
after-transaction function declares a single non-context parameter, the
contract chaincode passes it an instance of :class:`UndefinedInterface` when
the named function returned no success value.
"""

from __future__ import annotations


class UndefinedInterface:
    """Sentinel type used when a contract function returns no value."""

    _instance: "UndefinedInterface | None" = None

    def __new__(cls) -> "UndefinedInterface":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return "UndefinedInterface"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UndefinedInterface)

    def __hash__(self) -> int:
        return hash("UndefinedInterface")


__all__ = ["UndefinedInterface"]
