# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for the fabric_contract_api package.

These tests verify the high-level behaviour of the contract API without
needing a running Fabric peer: a minimal in-memory ``ChaincodeStub`` mock
is used to exercise ``ContractChaincode.invoke()``.

Run them with::

    python -m pytest tests/test_contract_api.py

or directly::

    python tests/test_contract_api.py
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional

# Allow running tests directly from the repository root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.fabric_contract_api import (  # noqa: E402
    Contract,
    ContractChaincode,
    JSONSerializer,
    TransactionContext,
    TransactionContextInterface,
)


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
        # Fall back to ``message`` for backward compat with the old
        # (buggy) shim that put bytes in ``message``.
        message = resp.message
        if isinstance(message, bytes):
            return message
        if isinstance(message, str):
            return message.encode("utf-8")
    return b""


class MockChaincodeStub:
    """Minimal ChaincodeStub implementation for tests."""

    # Shared store across invocations so that state survives between
    # successive ``invoke()`` calls within the same test.
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


# ---------------------------------------------------------------------------
# Sample contracts
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Asset:
    """A simple dataclass used as a structured argument/return type."""
    ID: str
    Owner: str
    Value: int


class AssetContract(Contract):
    Name: str = "AssetContract"

    def __init__(self) -> None:
        super().__init__()

    # ---------------- create / read / update ---------------------------

    async def create_asset(self, ctx: TransactionContextInterface, asset: Asset) -> None:
        key = asset.ID
        if await ctx.get_stub().get_state(key):
            raise ValueError(f"asset {key} already exists")
        payload = json.dumps({"ID": asset.ID, "Owner": asset.Owner, "Value": asset.Value}).encode()
        await ctx.get_stub().put_state(key, payload)

    async def read_asset(self, ctx: TransactionContextInterface, key: str) -> bytes:
        raw = await ctx.get_stub().get_state(key)
        if not raw:
            raise ValueError(f"asset {key} does not exist")
        return raw

    def get_evaluate_transactions(self) -> List[str]:
        return ["read_asset"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class ContractApiTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.contract = AssetContract()
        self.cc = ContractChaincode.new_chaincode(self.contract)
        # Sanity-check that the metadata includes the system contract.
        self.assertIn("AssetContract", self.cc._metadata.contracts)
        self.assertIn("org.hyperledger.fabric", self.cc._metadata.contracts)

    async def _invoke(self, function: str, *params: str):
        stub = MockChaincodeStub(function=function, params=list(params))
        return await self.cc.invoke(stub)

    async def test_create_and_read(self):
        asset_json = json.dumps({"ID": "asset1", "Owner": "Alice", "Value": 100})
        resp = await self._invoke("create_asset", asset_json)
        self.assertEqual(resp.status, 200, "create_asset should succeed")
        resp = await self._invoke("read_asset", "asset1")
        self.assertEqual(resp.status, 200)
        body = _read_response_payload(resp).decode("utf-8")
        parsed = json.loads(body)
        self.assertEqual(parsed["ID"], "asset1")
        self.assertEqual(parsed["Owner"], "Alice")
        self.assertEqual(parsed["Value"], 100)

    async def test_read_missing(self):
        resp = await self._invoke("read_asset", "missing")
        self.assertGreaterEqual(resp.status, 400, "reading a missing key should error")

    async def test_create_duplicate(self):
        asset_json = json.dumps({"ID": "asset2", "Owner": "Bob", "Value": 50})
        resp = await self._invoke("create_asset", asset_json)
        self.assertEqual(resp.status, 200, "first create should succeed")
        resp = await self._invoke("create_asset", asset_json)
        self.assertGreaterEqual(resp.status, 400, "second create should error")

    async def test_namespaced_call(self):
        asset_json = json.dumps({"ID": "asset3", "Owner": "Carol", "Value": 7})
        resp = await self._invoke("AssetContract:create_asset", asset_json)
        self.assertEqual(resp.status, 200)
        resp = await self._invoke("AssetContract:read_asset", "asset3")
        self.assertEqual(resp.status, 200)

    async def test_get_metadata_via_system_contract(self):
        resp = await self._invoke("org.hyperledger.fabric:get_metadata")
        self.assertEqual(resp.status, 200)
        body = _read_response_payload(resp).decode("utf-8")
        metadata = json.loads(body)
        self.assertIn("AssetContract", metadata["contracts"])
        self.assertIn("org.hyperledger.fabric", metadata["contracts"])
        # The "read_asset" transaction must be marked as evaluate.
        asset_meta = metadata["contracts"]["AssetContract"]
        read_tx = next(t for t in asset_meta["transactions"] if t["name"] == "read_asset")
        self.assertIn("EVALUATE", read_tx["tag"])

    async def test_unknown_function(self):
        resp = await self._invoke("nonexistent_function")
        self.assertGreaterEqual(resp.status, 400)

    async def test_json_serializer_round_trip(self):
        s = JSONSerializer()
        from src.fabric_contract_api.metadata import ParameterMetadata, ComponentMetadata
        value, err = s.from_string("true", bool, ParameterMetadata(name="param0", schema={"type": "boolean"}), ComponentMetadata())
        self.assertIsNone(err)
        self.assertEqual(value, True)
        s_val, err = s.to_string(123, int, None, None)
        self.assertIsNone(err)
        self.assertEqual(s_val, "123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
