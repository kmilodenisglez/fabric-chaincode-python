# SPDX-License-Identifier: Apache-2.0
"""Functional tests for the CCAAS-style asset-transfer-sbe example
(fabric_contract_api layer).

Exercises every transaction of :class:`AssetTransferSBEContract`:
``InitLedger``, ``CreateAsset``, ``ReadAsset``, ``UpdateAsset``,
``DeleteAsset``, ``TransferAsset``, ``AssetExists``.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import unittest
from typing import Dict, List, Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _REPO_ROOT)


def _load_example_module():
    """Load the SBE example ``main.py`` under a unique module name."""
    path = os.path.join(
        _REPO_ROOT,
        "examples", "ccaas", "fabric-contract-api",
        "asset-transfer-sbe", "main.py",
    )
    spec = importlib.util.spec_from_file_location("ccaas_sbe_example", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["ccaas_sbe_example"] = module
    spec.loader.exec_module(module)
    return module


example_main = _load_example_module()

from src.fabric_contract_api import (  # noqa: E402
    Contract,
    ContractChaincode,
)

Asset = example_main.Asset
AssetTransferSBEContract = example_main.AssetTransferSBEContract


def _read_response_payload(resp):
    """Return the bytes of a successful chaincode Response.

    ``peer chaincode query`` reads ``Response.payload`` and prints it to
    stdout — this helper mirrors that behaviour.
    """
    payload = resp.payload
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    if not payload:
        message = resp.message
        if isinstance(message, bytes):
            return message
        if isinstance(message, str):
            return message.encode("utf-8")
    return b""


# ---------------------------------------------------------------------------
# Mock stub
# ---------------------------------------------------------------------------


class _MockRangeIterator:
    def __init__(self, store: Dict[str, bytes], start_key: str, end_key: str):
        all_keys = sorted(store.keys())

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
    """Minimal ChaincodeStub implementation for tests."""

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


class AssetTransferSBETests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        MockChaincodeStub._shared_store = {}
        self.cc = ContractChaincode.new_chaincode(AssetTransferSBEContract())

    async def _invoke(self, function: str, *params: str):
        stub = MockChaincodeStub(function=function, params=list(params))
        return await self.cc.invoke(stub)

    # ----------------- happy path --------------------------------------

    async def test_init_ledger(self):
        resp = await self._invoke("InitLedger")
        self.assertEqual(resp.status, 200)
        # Two seed assets should exist.
        resp = await self._invoke("ReadAsset", "asset1")
        self.assertEqual(resp.status, 200)
        body = json.loads(_read_response_payload(resp).decode("utf-8"))
        self.assertEqual(body["id"], "asset1")
        self.assertEqual(body["value"], 100)
        self.assertEqual(body["owner"], "Tomoko")
        self.assertEqual(body["owner_org"], "Org1MSP")

    async def test_create_read_update_transfer_delete(self):
        # Create
        resp = await self._invoke("CreateAsset", "assetX", "150", "alice")
        self.assertEqual(resp.status, 200, "CreateAsset should succeed")
        # Read
        resp = await self._invoke("ReadAsset", "assetX")
        self.assertEqual(resp.status, 200)
        body = json.loads(_read_response_payload(resp).decode("utf-8"))
        self.assertEqual(body["value"], 150)
        # Update value
        resp = await self._invoke("UpdateAsset", "assetX", "200")
        self.assertEqual(resp.status, 200)
        resp = await self._invoke("ReadAsset", "assetX")
        body = json.loads(_read_response_payload(resp).decode("utf-8"))
        self.assertEqual(body["value"], 200)
        # Transfer
        resp = await self._invoke("TransferAsset", "assetX", "bob", "Org2MSP")
        self.assertEqual(resp.status, 200)
        resp = await self._invoke("ReadAsset", "assetX")
        body = json.loads(_read_response_payload(resp).decode("utf-8"))
        self.assertEqual(body["owner"], "bob")
        self.assertEqual(body["owner_org"], "Org2MSP")
        # Exists
        resp = await self._invoke("AssetExists", "assetX")
        self.assertEqual(resp.status, 200)
        self.assertEqual(_read_response_payload(resp).decode("utf-8"), "true")
        # Delete
        resp = await self._invoke("DeleteAsset", "assetX")
        self.assertEqual(resp.status, 200)
        # Now it shouldn't exist
        resp = await self._invoke("AssetExists", "assetX")
        self.assertEqual(resp.status, 200)
        self.assertEqual(_read_response_payload(resp).decode("utf-8"), "false")

    async def test_create_duplicate(self):
        resp = await self._invoke("CreateAsset", "dup", "10", "alice")
        self.assertEqual(resp.status, 200)
        resp = await self._invoke("CreateAsset", "dup", "20", "bob")
        self.assertGreaterEqual(resp.status, 400)

    async def test_update_missing(self):
        resp = await self._invoke("UpdateAsset", "nope", "1")
        self.assertGreaterEqual(resp.status, 400)

    async def test_transfer_missing(self):
        resp = await self._invoke("TransferAsset", "nope", "bob", "Org2MSP")
        self.assertGreaterEqual(resp.status, 400)

    async def test_read_missing(self):
        resp = await self._invoke("ReadAsset", "nope")
        self.assertGreaterEqual(resp.status, 400)

    async def test_delete_missing(self):
        resp = await self._invoke("DeleteAsset", "nope")
        self.assertGreaterEqual(resp.status, 400)

    async def test_namespaced_call(self):
        resp = await self._invoke("AssetTransferSBE:CreateAsset", "ns1", "5", "carol")
        self.assertEqual(resp.status, 200)
        resp = await self._invoke("AssetTransferSBE:ReadAsset", "ns1")
        self.assertEqual(resp.status, 200)
        body = json.loads(_read_response_payload(resp).decode("utf-8"))
        self.assertEqual(body["owner"], "carol")

    async def test_get_metadata(self):
        resp = await self._invoke("org.hyperledger.fabric:get_metadata")
        self.assertEqual(resp.status, 200)
        metadata = json.loads(_read_response_payload(resp).decode("utf-8"))
        self.assertIn("AssetTransferSBE", metadata["contracts"])
        contract_meta = metadata["contracts"]["AssetTransferSBE"]
        names = {t["name"] for t in contract_meta["transactions"]}
        self.assertEqual(names, {
            "InitLedger", "CreateAsset", "ReadAsset",
            "UpdateAsset", "DeleteAsset", "TransferAsset", "AssetExists",
        })
        # ReadAsset and AssetExists should be tagged as EVALUATE.
        for tx in contract_meta["transactions"]:
            if tx["name"] in ("ReadAsset", "AssetExists"):
                self.assertIn("EVALUATE", tx["tag"])
            else:
                self.assertIn("SUBMIT", tx["tag"])

    async def test_unknown_function(self):
        resp = await self._invoke("NoSuchFunction")
        self.assertGreaterEqual(resp.status, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
