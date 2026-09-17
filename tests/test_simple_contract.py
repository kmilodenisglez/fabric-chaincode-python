# SPDX-License-Identifier: Apache-2.0
"""Functional tests for the CCAAS-style simple_contract.py example.

These tests exercise every transaction of :class:`AssetContract` using an
in-memory :class:`MockChaincodeStub` that also implements
``get_state_by_range`` so that :meth:`AssetContract.get_all_assets` can be
exercised end-to-end.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional

# Allow running tests directly from the repository root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "examples")))

from simple_contract import Asset  # noqa: E402
from src.fabric_contract_api import (  # noqa: E402
    Contract,
    ContractChaincode,
)


# ---------------------------------------------------------------------------
# Mock stub with get_state_by_range support
# ---------------------------------------------------------------------------


class _MockRangeIterator:
    """Async iterator over the items in a key range."""

    def __init__(self, store: Dict[str, bytes], start_key: str, end_key: str):
        # Sort the keys lexicographically (Fabric does the same).
        all_keys = sorted(store.keys())
        # Filter by the requested range.  Empty bounds mean "unbounded".
        def in_range(k: str) -> bool:
            if start_key and k < start_key:
                return False
            if end_key and k >= end_key:
                return False
            return True
        self._items = [store[k] for k in all_keys if in_range(k)]
        self._keys = [k for k in all_keys if in_range(k)]
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._items):
            raise StopAsyncIteration
        kv = _MockKV(self._keys[self._idx], self._items[self._idx])
        self._idx += 1
        return kv


class _MockKV:
    def __init__(self, key: str, value: bytes):
        self.key = key
        self.value = value


class MockChaincodeStub:
    """Minimal ChaincodeStub implementation for tests.

    Supports get_state / put_state / delete_state / get_state_by_range /
    get_function_and_parameters / get_creator / get_channel_id / get_txid —
    everything the contract API needs to dispatch transactions.
    """

    _shared_store: Dict[str, bytes] = {}

    def __init__(self, function: str = "", params: Optional[List[str]] = None,
                 channel_id: str = "test-channel", tx_id: str = "tx-1234"):
        self._function = function
        self._params = list(params or [])
        self._channel_id = channel_id
        self._tx_id = tx_id
        self._store = MockChaincodeStub._shared_store

    def get_function_and_parameters(self):
        return self._function, self._params

    def get_channel_id(self) -> str:
        return self._channel_id

    def get_txid(self) -> str:
        return self._tx_id

    def get_creator(self):
        return {"mspid": "Org1MSP", "idBytes": b"fake-cert"}

    def get_tx_timestamp(self):
        return None

    def get_transient(self):
        return {}

    async def get_state(self, key: str) -> bytes:
        return self._store.get(key)

    async def put_state(self, key: str, value: bytes) -> None:
        self._store[key] = bytes(value) if isinstance(value, (bytearray, memoryview)) else value

    async def delete_state(self, key: str) -> None:
        self._store.pop(key, None)

    async def get_state_by_range(self, start_key: str, end_key: str):
        return _MockRangeIterator(dict(self._store), start_key, end_key)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class SimpleContractTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Clear the shared store before each test.
        MockChaincodeStub._shared_store = {}
        from simple_contract import AssetContract
        self.cc = ContractChaincode.new_chaincode(AssetContract())

    async def _invoke(self, function: str, *params: str):
        stub = MockChaincodeStub(function=function, params=list(params))
        return await self.cc.invoke(stub)

    async def test_init_ledger(self):
        resp = await self._invoke("init_ledger")
        self.assertEqual(resp.status, 200, "init_ledger should succeed")
        # Now check that the assets are present.
        resp = await self._invoke("get_all_assets")
        self.assertEqual(resp.status, 200)
        msg = resp.message
        body = msg.decode("utf-8") if isinstance(msg, bytes) else msg
        assets = json.loads(body)
        self.assertEqual(len(assets), 6, "init_ledger should create 6 sample assets")
        self.assertEqual(assets[0]["id"], "asset1")
        self.assertEqual(assets[0]["color"], "blue")

    async def test_create_read_update_delete(self):
        asset = {"id": "asset100", "color": "pink", "size": 7,
                  "owner": "Alice", "appraised_value": 800}
        # Create
        resp = await self._invoke("create_asset", json.dumps(asset))
        self.assertEqual(resp.status, 200, "create should succeed")
        # Read
        resp = await self._invoke("read_asset", "asset100")
        self.assertEqual(resp.status, 200, "read should succeed")
        msg = resp.message
        body = msg.decode("utf-8") if isinstance(msg, bytes) else msg
        self.assertEqual(json.loads(body), asset)
        # Update
        updated = dict(asset)
        updated["color"] = "green"
        resp = await self._invoke("update_asset", json.dumps(updated))
        self.assertEqual(resp.status, 200, "update should succeed")
        # Read again to verify
        resp = await self._invoke("read_asset", "asset100")
        msg = resp.message
        body = msg.decode("utf-8") if isinstance(msg, bytes) else msg
        self.assertEqual(json.loads(body)["color"], "green")
        # Delete
        resp = await self._invoke("delete_asset", "asset100")
        self.assertEqual(resp.status, 200, "delete should succeed")
        # Subsequent read should fail
        resp = await self._invoke("read_asset", "asset100")
        self.assertGreaterEqual(resp.status, 400, "read after delete should error")

    async def test_create_duplicate(self):
        asset = {"id": "asset200", "color": "white", "size": 3,
                  "owner": "Bob", "appraised_value": 50}
        resp = await self._invoke("create_asset", json.dumps(asset))
        self.assertEqual(resp.status, 200, "first create should succeed")
        resp = await self._invoke("create_asset", json.dumps(asset))
        self.assertGreaterEqual(resp.status, 400, "duplicate create should error")

    async def test_get_all_assets_empty(self):
        resp = await self._invoke("get_all_assets")
        self.assertEqual(resp.status, 200)
        msg = resp.message
        body = msg.decode("utf-8") if isinstance(msg, bytes) else msg
        self.assertEqual(json.loads(body), [])

    async def test_namespaced_call(self):
        asset = {"id": "asset300", "color": "gold", "size": 1,
                  "owner": "Carol", "appraised_value": 1000}
        resp = await self._invoke("AssetContract:create_asset", json.dumps(asset))
        self.assertEqual(resp.status, 200)
        resp = await self._invoke("AssetContract:read_asset", "asset300")
        self.assertEqual(resp.status, 200)
        msg = resp.message
        body = msg.decode("utf-8") if isinstance(msg, bytes) else msg
        self.assertEqual(json.loads(body)["id"], "asset300")

    async def test_get_metadata(self):
        resp = await self._invoke("org.hyperledger.fabric:get_metadata")
        self.assertEqual(resp.status, 200)
        msg = resp.message
        body = msg.decode("utf-8") if isinstance(msg, bytes) else msg
        metadata = json.loads(body)
        self.assertIn("AssetContract", metadata["contracts"])
        asset_meta = metadata["contracts"]["AssetContract"]
        names = {t["name"] for t in asset_meta["transactions"]}
        self.assertEqual(names, {
            "init_ledger", "create_asset", "read_asset",
            "update_asset", "delete_asset", "get_all_assets",
        })
        # Verify the EVALUATE tags are set correctly.
        for tx in asset_meta["transactions"]:
            if tx["name"] in ("read_asset", "get_all_assets"):
                self.assertIn("EVALUATE", tx["tag"])
            else:
                self.assertIn("SUBMIT", tx["tag"])

    async def test_unknown_function(self):
        resp = await self._invoke("nonexistent_function")
        self.assertGreaterEqual(resp.status, 400)

    async def test_asset_dataclass_serialisation(self):
        """Verify the Asset dataclass can be round-tripped through JSON."""
        asset = Asset(id="x", color="red", size=1, owner="me", appraised_value=2)
        s = json.dumps({
            "id": asset.id, "color": asset.color, "size": asset.size,
            "owner": asset.owner, "appraised_value": asset.appraised_value,
        })
        d = json.loads(s)
        self.assertEqual(d["id"], "x")
        self.assertEqual(d["color"], "red")
        self.assertEqual(d["size"], 1)
        self.assertEqual(d["owner"], "me")
        self.assertEqual(d["appraised_value"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
