# SPDX-License-Identifier: Apache-2.0
"""Sample contract demonstrating the fabric_contract_api.

Mirrors the layout of Go's ``internal/functionaltests/contracts/simplecontract``.
"""

from __future__ import annotations

import asyncio
import sys
from typing import List

# Allow running this file directly from the repository root.
sys.path.insert(0, ".")

from src.fabric_contract_api import (  # noqa: E402
    Contract,
    ContractChaincode,
    TransactionContextInterface,
)


class SimpleContract(Contract):
    """A tiny key/value contract used to exercise the contract API."""

    Name: str = "SimpleContract"

    # ------------------------------------------------------------------
    # Transaction functions
    # ------------------------------------------------------------------

    async def create(self, ctx: TransactionContextInterface, key: str) -> None:
        """Initialise a key in the world state with the value "Initialised"."""
        if await ctx.get_stub().get_state(key):
            raise ValueError(f"cannot create key. Key with id {key} already exists")
        await ctx.get_stub().put_state(key, b"Initialised")

    async def update(self, ctx: TransactionContextInterface, key: str, value: bytes) -> None:
        """Update an existing key in the world state."""
        if not await ctx.get_stub().get_state(key):
            raise ValueError(f"cannot update key. Key with id {key} does not exist")
        await ctx.get_stub().put_state(key, value)

    async def read(self, ctx: TransactionContextInterface, key: str) -> bytes:
        """Return the raw bytes stored at *key*."""
        existing = await ctx.get_stub().get_state(key)
        if not existing:
            raise ValueError(f"cannot read key. Key with id {key} does not exist")
        return existing

    # ------------------------------------------------------------------
    # Optional metadata hints
    # ------------------------------------------------------------------

    def get_evaluate_transactions(self) -> List[str]:
        return ["read"]


if __name__ == "__main__":
    cc = ContractChaincode.new_chaincode(SimpleContract())
    metadata = cc._metadata.to_json()
    print("== Generated metadata ==")
    print(metadata)
