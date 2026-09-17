#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Asset Transfer SBE (fabric_contract_api high-level API, CCAAS).

This is the contract-API counterpart of
``examples/ccaas/fabric-shim/asset-transfer-sbe/main.py``.  It implements
the same transaction set as ``fabric-samples/asset-transfer-sbe``:

* ``CreateAsset(assetId, value, owner)`` — create a new asset.
* ``ReadAsset(assetId)`` — return the stored JSON for an asset.
* ``UpdateAsset(assetId, newValue)`` — update the value of an asset.
* ``DeleteAsset(assetId)`` — remove an asset from the ledger.
* ``TransferAsset(assetId, newOwner, newOwnerOrg)`` — change ownership.
* ``AssetExists(assetId)`` — return ``true``/``false``.
* ``InitLedger()`` — seed the ledger with two sample assets.

Compared to the fabric-shim version, the contract API:

* declares each transaction as a method on :class:`AssetTransferSBEContract`;
* lets the framework dispatch Init/Invoke calls automatically;
* exposes chaincode metadata via the system contract
  ``org.hyperledger.fabric:get_metadata``;
* validates parameter and return types through the JSON serializer.

Deploy this chaincode as a CCAAS in Fabric by setting the following
environment variables before launching it:

* ``CHAINCODE_SERVER_ADDRESS``  e.g. ``0.0.0.0:9999``
* ``CHAINCODE_ID``             the chaincode ID returned by ``peer lifecycle``

Then simply run::

    python main.py

NOTE: This example mirrors the SBE fields and the transfer flow but does
**not** apply key-level endorsement policy from code, because the Python
shim does not yet expose ``set_state_validation_parameter``.  The Go
``asset-transfer-sbe`` sample does apply SBE policies via
``shim.SetStateValidationParameter``.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

# Make sure the repository root is on ``sys.path`` so that the
# ``src.fabric_contract_api`` packages can be imported when the file is
# run directly.
_HERE = Path(__file__).resolve().parent
REPO_ROOT = None
for parent in [_HERE, *_HERE.parents]:
    if (parent / "src" / "fabric_contract_api").is_dir():
        REPO_ROOT = parent
        break
if REPO_ROOT is None:
    REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.fabric_contract_api import (  # noqa: E402
    Contract,
    ContractChaincode,
    TransactionContextInterface,
)


# ---------------------------------------------------------------------------
# Asset dataclass
# ---------------------------------------------------------------------------


@dataclass
class Asset:
    """An SBE-style asset.

    Field names follow the Go ``asset-transfer-sbe`` convention
    (ID/Value/Owner/OwnerOrg) so the on-chain JSON matches what the
    fabric-shim version of this sample produces.
    """

    id: str = ""
    value: int = 0
    owner: str = ""
    owner_org: str = ""


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


class AssetTransferSBEContract(Contract):
    """Asset transfer contract mirroring ``fabric-samples/asset-transfer-sbe``.

    Every public method becomes a callable transaction.  The contract API
    inspects each method's parameter and return-type annotations and
    converts the string args coming from the peer into typed Python values
    via the JSON serializer.
    """

    Name: str = "AssetTransferSBE"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _exists(self, ctx: TransactionContextInterface,
                       asset_id: str) -> bool:
        return bool(await ctx.get_stub().get_state(asset_id))

    async def _read_asset(self, ctx: TransactionContextInterface,
                          asset_id: str):
        raw = await ctx.get_stub().get_state(asset_id)
        if not raw:
            return None
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return None
        return Asset(
            id=str(data.get("id", asset_id)),
            value=int(data.get("value", 0) or 0),
            owner=str(data.get("owner", "")),
            owner_org=str(data.get("owner_org", "")),
        )

    async def _write_asset(self, ctx: TransactionContextInterface,
                            asset: Asset) -> None:
        # On-chain JSON uses lowercase field names matching the Asset
        # dataclass — this is what the contract API's auto-generated schema
        # also advertises, so clients querying the metadata see consistent
        # field names.
        payload = json.dumps({
            "id": asset.id,
            "value": asset.value,
            "owner": asset.owner,
            "owner_org": asset.owner_org,
        }).encode("utf-8")
        await ctx.get_stub().put_state(asset.id, payload)

    @staticmethod
    def _client_org_id(ctx: TransactionContextInterface) -> str:
        creator = ctx.get_stub().get_creator() or {}
        if isinstance(creator, dict):
            return creator.get("mspid") or "Org1MSP"
        return "Org1MSP"

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def InitLedger(self, ctx: TransactionContextInterface) -> None:
        """Seed the ledger with two sample assets."""
        seed = [
            Asset(id="asset1", value=100, owner="Tomoko", owner_org="Org1MSP"),
            Asset(id="asset2", value=200, owner="Brad", owner_org="Org1MSP"),
        ]
        for asset in seed:
            await self._write_asset(ctx, asset)

    async def CreateAsset(self, ctx: TransactionContextInterface,
                           asset_id: str, value: int, owner: str) -> None:
        """Create a new asset.

        ``asset_id`` and ``owner`` are strings; ``value`` is converted to
        int by the JSON serializer.
        """
        if await self._exists(ctx, asset_id):
            raise ValueError(f"The asset {asset_id} already exists")
        owner_org = self._client_org_id(ctx)
        await self._write_asset(ctx, Asset(
            id=asset_id, value=int(value), owner=owner, owner_org=owner_org,
        ))

    async def ReadAsset(self, ctx: TransactionContextInterface,
                         asset_id: str) -> Asset:
        """Read an asset from the ledger."""
        asset = await self._read_asset(ctx, asset_id)
        if asset is None:
            raise ValueError(f"The asset {asset_id} does not exist")
        return asset

    async def UpdateAsset(self, ctx: TransactionContextInterface,
                           asset_id: str, new_value: int) -> None:
        """Update the ``Value`` field of an existing asset."""
        asset = await self._read_asset(ctx, asset_id)
        if asset is None:
            raise ValueError(f"The asset {asset_id} does not exist")
        asset.value = int(new_value)
        await self._write_asset(ctx, asset)

    async def DeleteAsset(self, ctx: TransactionContextInterface,
                           asset_id: str) -> None:
        """Delete an asset from the ledger."""
        if not await self._exists(ctx, asset_id):
            raise ValueError(f"The asset {asset_id} does not exist")
        await ctx.get_stub().delete_state(asset_id)

    async def TransferAsset(self, ctx: TransactionContextInterface,
                              asset_id: str, new_owner: str,
                              new_owner_org: str) -> None:
        """Transfer ownership of an asset to a new owner / org."""
        asset = await self._read_asset(ctx, asset_id)
        if asset is None:
            raise ValueError(f"The asset {asset_id} does not exist")
        asset.owner = new_owner
        asset.owner_org = new_owner_org
        await self._write_asset(ctx, asset)

    async def AssetExists(self, ctx: TransactionContextInterface,
                           asset_id: str) -> bool:
        """Return ``true`` if the asset exists, ``false`` otherwise."""
        return await self._exists(ctx, asset_id)

    # ------------------------------------------------------------------
    # Optional metadata hints
    # ------------------------------------------------------------------

    def get_evaluate_transactions(self) -> List[str]:
        """Mark read-only transactions for the metadata.

        ``ReadAsset``, ``AssetExists`` are pure queries — clients should
        call them via ``peer chaincode query`` rather than ``invoke``.
        """
        return ["ReadAsset", "AssetExists"]


# ---------------------------------------------------------------------------
# CCAAS entry point
# ---------------------------------------------------------------------------


def build_chaincode() -> ContractChaincode:
    """Build the :class:`ContractChaincode` from :class:`AssetTransferSBEContract`."""
    return ContractChaincode.new_chaincode(AssetTransferSBEContract())


def main() -> None:
    """Build the contract chaincode and start the gRPC server (CCAAS)."""
    cc = build_chaincode()
    cc.start()


if __name__ == "__main__":
    main()
