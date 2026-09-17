#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Basic Fabric Contract-API Example (CCAAS, fabric_contract_api).

This is the contract-API counterpart of
``examples/ccaas/fabric-shim/asset-transfer-basic/main.py``.  It exposes
the same asset-management transactions (InitLedger, CreateAsset, ReadAsset,
UpdateAsset, DeleteAsset, GetAllAssets) but uses the high-level
``fabric_contract_api`` package, which:

* reflects over the public methods of :class:`AssetContract`;
* builds a JSON metadata document exposing them through the
  ``org.hyperledger.fabric:get_metadata`` system contract;
* dispatches incoming Init/Invoke transactions to the appropriate method,
  converting string arguments to the function's parameter types via the
  JSON serializer.

Deploy this chaincode as a CCAAS in Fabric by setting the following
environment variables before launching it:

* ``CHAINCODE_SERVER_ADDRESS``  e.g. ``0.0.0.0:9999``
* ``CHAINCODE_ID``             the chaincode ID returned by ``peer lifecycle``
* (optional TLS) ``CORE_TLS_CLIENT_KEY_PATH``,
  ``CORE_TLS_CLIENT_CERT_PATH``, ``CORE_PEER_TLS_ROOTCERT_FILE``

Then simply run::

    python main.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Make sure the repository root is on ``sys.path`` so that the
# ``src.fabric_contract_api`` packages can be imported when the file is
# run directly.  Walk up the parent chain looking for the directory that
# contains ``src/``.
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
    """Represents a simple asset with basic properties.

    Used both as a transaction parameter and as a return type.  Because it
    is a dataclass, the JSON serializer will automatically convert between
    the JSON form coming from the client and the Python instance.
    """

    id: str = ""
    color: str = ""
    size: int = 0
    owner: str = ""
    appraised_value: int = 0


# ---------------------------------------------------------------------------
# AssetContract
# ---------------------------------------------------------------------------


class AssetContract(Contract):
    """Basic asset management contract.

    Mirrors the behaviour of ``BasicAssetChaincode`` in
    ``examples/ccaas/fabric-shim/asset-transfer-basic/main.py`` but
    exposes its operations as contract transactions so that the
    :class:`ContractChaincode` dispatcher can route Init/Invoke calls
    automatically and so that the contract's metadata is reflected into the
    chaincode's ``org.hyperledger.fabric:get_metadata`` system contract.
    """

    Name: str = "AssetContract"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _read_asset(self, ctx: TransactionContextInterface,
                          asset_id: str) -> Optional[Asset]:
        """Return the :class:`Asset` stored at *asset_id* or ``None``."""
        raw = await ctx.get_stub().get_state(asset_id)
        if not raw:
            return None
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return None
        return Asset(
            id=str(data.get("id", asset_id)),
            color=str(data.get("color", "")),
            size=int(data.get("size", 0) or 0),
            owner=str(data.get("owner", "")),
            appraised_value=int(data.get("appraised_value", 0) or 0),
        )

    async def _write_asset(self, ctx: TransactionContextInterface,
                            asset: Asset) -> None:
        """Serialise *asset* and put_state on its key."""
        payload = json.dumps({
            "id": asset.id,
            "color": asset.color,
            "size": asset.size,
            "owner": asset.owner,
            "appraised_value": asset.appraised_value,
        }).encode("utf-8")
        await ctx.get_stub().put_state(asset.id, payload)

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def InitLedger(self, ctx: TransactionContextInterface) -> None:
        """Populate the ledger with a set of sample assets.

        Called automatically when the chaincode is instantiated with the
        ``InitLedger`` action; can also be called directly via Invoke.
        """
        samples = [
            Asset("asset1", "blue", 5, "Tomoko", 300),
            Asset("asset2", "red", 5, "Brad", 400),
            Asset("asset3", "green", 10, "Jin Soo", 500),
            Asset("asset4", "yellow", 10, "Max", 500),
            Asset("asset5", "black", 15, "Adriana", 700),
            Asset("asset6", "purple", 8, "Michel", 600),
        ]
        for asset in samples:
            await self._write_asset(ctx, asset)

    async def CreateAsset(self, ctx: TransactionContextInterface,
                             asset_id: str, color: str, size: int,
                             owner: str, appraised_value: int) -> None:
        """Create a new asset on the ledger.

        Mirrors the Go ``asset-transfer-basic`` signature — five separate
        scalar args, so clients can invoke it with::

            peer chaincode invoke -c \\
              '{"Args":["CreateAsset","asset1","blue","10","alice","100"]}'

        Errors out if an asset with the same ID already exists.
        """
        asset = Asset(
            id=asset_id,
            color=color,
            size=int(size),
            owner=owner,
            appraised_value=int(appraised_value),
        )
        existing = await ctx.get_stub().get_state(asset.id)
        if existing:
            raise ValueError(f"asset {asset.id} already exists")
        await self._write_asset(ctx, asset)

    async def ReadAsset(self, ctx: TransactionContextInterface,
                           key: str) -> Asset:
        """Read an asset from the ledger."""
        asset = await self._read_asset(ctx, key)
        if asset is None:
            raise ValueError(f"asset {key} does not exist")
        return asset

    async def UpdateAsset(self, ctx: TransactionContextInterface,
                             asset_id: str, color: str, size: int,
                             owner: str, appraised_value: int) -> None:
        """Update an existing asset on the ledger.

        Mirrors the Go ``asset-transfer-basic`` signature — five separate
        scalar args, so clients can invoke it the same way as ``CreateAsset``.

        Errors out if no asset exists at ``asset_id``.
        """
        asset = Asset(
            id=asset_id,
            color=color,
            size=int(size),
            owner=owner,
            appraised_value=int(appraised_value),
        )
        existing = await ctx.get_stub().get_state(asset.id)
        if not existing:
            raise ValueError(
                f"cannot update asset {asset.id}: does not exist"
            )
        await self._write_asset(ctx, asset)

    async def DeleteAsset(self, ctx: TransactionContextInterface,
                             key: str) -> None:
        """Delete an asset from the ledger."""
        existing = await ctx.get_stub().get_state(key)
        if not existing:
            raise ValueError(
                f"cannot delete asset {key}: does not exist"
            )
        await ctx.get_stub().delete_state(key)

    async def GetAllAssets(self, ctx: TransactionContextInterface
                               ) -> List[Asset]:
        """Return every asset currently stored in the world state.

        Uses :meth:`ChaincodeStub.get_state_by_range` to iterate over the
        whole key range — the empty-string bounds mean "unbounded".
        """
        results: List[Asset] = []
        iterator = await ctx.get_stub().get_state_by_range("", "")
        async for kv in iterator:
            try:
                data = json.loads(kv.value.decode("utf-8"))
            except Exception:
                # Skip non-JSON entries (e.g. system keys).
                continue
            results.append(Asset(
                id=str(data.get("id", kv.key)),
                color=str(data.get("color", "")),
                size=int(data.get("size", 0) or 0),
                owner=str(data.get("owner", "")),
                appraised_value=int(data.get("appraised_value", 0) or 0),
            ))
        return results

    # ------------------------------------------------------------------
    # Optional metadata hints
    # ------------------------------------------------------------------

    def get_evaluate_transactions(self) -> List[str]:
        """Mark read-only transactions for the metadata.

        Transactions listed here will be tagged as ``EVALUATE`` in the
        metadata, signalling to clients that they should be invoked via
        ``peer chaincode query`` rather than ``peer chaincode invoke``.
        """
        return ["ReadAsset", "GetAllAssets"]


# ---------------------------------------------------------------------------
# CCAAS entry point
# ---------------------------------------------------------------------------


def build_chaincode() -> ContractChaincode:
    """Build the :class:`ContractChaincode` from :class:`AssetContract`."""
    return ContractChaincode.new_chaincode(AssetContract())


def main() -> None:
    """Build the contract chaincode and start the gRPC server (CCAAS)."""
    cc = build_chaincode()
    # ``ContractChaincode.start`` reads ``CHAINCODE_SERVER_ADDRESS`` and
    # ``CHAINCODE_ID`` from the environment, mirroring Go's
    # ``ContractChaincode.Start``.
    cc.start()


if __name__ == "__main__":
    main()
