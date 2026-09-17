# SPDX-License-Identifier: Apache-2.0
"""Functional tests for the CCAAS-style asset-transfer-basic example
(fabric_contract_api layer).

These tests exercise every transaction of :class:`AssetContract` using an
in-memory :class:`MockChaincodeStub` that also implements
``get_state_by_range`` so that :meth:`AssetContract.GetAllAssets` can be
exercised end-to-end.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional

# Allow running tests directly from the repository root.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _REPO_ROOT)


def _load_example_module():
    """Load the example ``main.py`` under a unique module name.

    Using ``importlib.util.spec_from_file_location`` lets us avoid clashes
    with other test files that also need to import a ``main.py`` example.
    """
    path = os.path.join(
        _REPO_ROOT,
        "examples", "ccaas", "fabric-contract-api",
        "asset-transfer-basic", "main.py",
    )
    spec = importlib.util.spec_from_file_location("ccaas_basic_example", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["ccaas_basic_example"] = module
    spec.loader.exec_module(module)
    return module


example_main = _load_example_module()

from src.fabric_contract_api import (  # noqa: E402
    Contract,
    ContractChaincode,
)

# Re-export for convenience.
Asset = example_main.Asset
AssetContract = example_main.AssetContract


def _read_response_payload(resp):
    """Return the bytes of a successful chaincode Response.

    ``peer chaincode query`` reads ``Response.payload`` (the bytes field)
    and prints it to stdout.  This helper mirrors that behaviour so tests
    match what clients see.
    """
    payload = resp.payload
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    if not payload:
        # Fall back to ``message`` for backward compat.
        message = resp.message
        if isinstance(message, bytes):
            return message
        if isinstance(message, str):
            return message.encode("utf-8")
    return b""


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
        self.cc = ContractChaincode.new_chaincode(AssetContract())

    async def _invoke(self, function: str, *params: str):
        stub = MockChaincodeStub(function=function, params=list(params))
        return await self.cc.invoke(stub)

    async def test_init_ledger(self):
        resp = await self._invoke("InitLedger")
        self.assertEqual(resp.status, 200, "InitLedger should succeed")
        # Now check that the assets are present.
        resp = await self._invoke("GetAllAssets")
        self.assertEqual(resp.status, 200)
        assets = json.loads(_read_response_payload(resp).decode("utf-8"))
        self.assertEqual(len(assets), 6, "InitLedger should create 6 sample assets")
        self.assertEqual(assets[0]["id"], "asset1")
        self.assertEqual(assets[0]["color"], "blue")

    async def test_create_read_update_delete(self):
        asset = {"id": "asset100", "color": "pink", "size": 7,
                  "owner": "Alice", "appraised_value": 800}
        # Create
        resp = await self._invoke("CreateAsset", "asset100", "pink", "7", "Alice", "800")
        self.assertEqual(resp.status, 200, "create should succeed")
        # Read
        resp = await self._invoke("ReadAsset", "asset100")
        self.assertEqual(resp.status, 200, "read should succeed")
        self.assertEqual(json.loads(_read_response_payload(resp).decode("utf-8")), asset)
        # Update
        updated = dict(asset)
        updated["color"] = "green"
        resp = await self._invoke("UpdateAsset", "asset100", "green", "7", "Alice", "800")
        self.assertEqual(resp.status, 200, "update should succeed")
        # Read again to verify
        resp = await self._invoke("ReadAsset", "asset100")
        self.assertEqual(
            json.loads(_read_response_payload(resp).decode("utf-8"))["color"],
            "green",
        )
        # Delete
        resp = await self._invoke("DeleteAsset", "asset100")
        self.assertEqual(resp.status, 200, "delete should succeed")
        # Subsequent read should fail
        resp = await self._invoke("ReadAsset", "asset100")
        self.assertGreaterEqual(resp.status, 400, "read after delete should error")

    async def test_create_duplicate(self):
        asset = {"id": "asset200", "color": "white", "size": 3,
                  "owner": "Bob", "appraised_value": 50}
        resp = await self._invoke("CreateAsset", "asset200", "white", "3", "Bob", "50")
        self.assertEqual(resp.status, 200, "first create should succeed")
        resp = await self._invoke("CreateAsset", "asset200", "white", "3", "Bob", "50")
        self.assertGreaterEqual(resp.status, 400, "duplicate create should error")

    async def test_get_all_assets_empty(self):
        resp = await self._invoke("GetAllAssets")
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(_read_response_payload(resp).decode("utf-8")), [])

    async def test_namespaced_call(self):
        asset = {"id": "asset300", "color": "gold", "size": 1,
                  "owner": "Carol", "appraised_value": 1000}
        resp = await self._invoke("AssetContract:CreateAsset", "asset300", "gold", "1", "Carol", "1000")
        self.assertEqual(resp.status, 200)
        resp = await self._invoke("AssetContract:ReadAsset", "asset300")
        self.assertEqual(resp.status, 200)
        self.assertEqual(
            json.loads(_read_response_payload(resp).decode("utf-8"))["id"],
            "asset300",
        )

    async def test_get_metadata(self):
        resp = await self._invoke("org.hyperledger.fabric:get_metadata")
        self.assertEqual(resp.status, 200)
        metadata = json.loads(_read_response_payload(resp).decode("utf-8"))
        self.assertIn("AssetContract", metadata["contracts"])
        asset_meta = metadata["contracts"]["AssetContract"]
        names = {t["name"] for t in asset_meta["transactions"]}
        self.assertEqual(names, {
            "InitLedger", "CreateAsset", "ReadAsset",
            "UpdateAsset", "DeleteAsset", "GetAllAssets",
        })
        # Verify the EVALUATE tags are set correctly.
        for tx in asset_meta["transactions"]:
            if tx["name"] in ("ReadAsset", "GetAllAssets"):
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
