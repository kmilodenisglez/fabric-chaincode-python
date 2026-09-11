#!/usr/bin/env python3
# Copyright the fabric-chaincode-python contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Asset Transfer SBE style chaincode for CCAAS.

This follows the function names from fabric-samples asset-transfer-sbe.
"""

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fabric_protos_python.peer import proposal_response_pb2 as pb
from src.fabric_shim.interfaces import Chaincode, ChaincodeStubInterface
from src.fabric_shim.response import ResponseCode
from src.fabric_shim.server import start

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AssetTransferSBEChaincode(Chaincode):
    async def init(self, stub: ChaincodeStubInterface) -> pb.Response:
        return pb.Response(status=ResponseCode.OK)

    async def invoke(self, stub: ChaincodeStubInterface) -> pb.Response:
        fn, args = stub.get_function_and_parameters()
        try:
            if fn == "CreateAsset":
                if len(args) != 3:
                    return self._error("CreateAsset requires 3 arguments: assetId, value, owner")
                return await self.create_asset(stub, args[0], args[1], args[2])

            if fn == "ReadAsset":
                if len(args) != 1:
                    return self._error("ReadAsset requires 1 argument: assetId")
                return await self.read_asset(stub, args[0])

            if fn == "UpdateAsset":
                if len(args) != 2:
                    return self._error("UpdateAsset requires 2 arguments: assetId, newValue")
                return await self.update_asset(stub, args[0], args[1])

            if fn == "DeleteAsset":
                if len(args) != 1:
                    return self._error("DeleteAsset requires 1 argument: assetId")
                return await self.delete_asset(stub, args[0])

            if fn == "TransferAsset":
                if len(args) != 3:
                    return self._error("TransferAsset requires 3 arguments: assetId, newOwner, newOwnerOrg")
                return await self.transfer_asset(stub, args[0], args[1], args[2])

            if fn == "AssetExists":
                if len(args) != 1:
                    return self._error("AssetExists requires 1 argument: assetId")
                exists = await self.asset_exists(stub, args[0])
                return pb.Response(status=ResponseCode.OK, payload=str(exists).lower().encode())

            if fn == "InitLedger":
                return await self.init_ledger(stub)

            return self._error(f"method {fn} not supported")
        except ValueError as exc:
            return self._error(str(exc))
        except Exception as exc:  # explicit error propagation to peer
            logger.exception("Invoke failed")
            return self._error(str(exc))

    async def init_ledger(self, stub: ChaincodeStubInterface) -> pb.Response:
        seed = [
            {"ID": "asset1", "Value": 100, "Owner": "Tomoko", "OwnerOrg": "Org1MSP"},
            {"ID": "asset2", "Value": 200, "Owner": "Brad", "OwnerOrg": "Org1MSP"},
        ]
        for asset in seed:
            await stub.put_state(asset["ID"], json.dumps(asset).encode())
        return pb.Response(status=ResponseCode.OK)

    async def create_asset(self, stub: ChaincodeStubInterface, asset_id: str, value: str, owner: str) -> pb.Response:
        if await self.asset_exists(stub, asset_id):
            return self._error(f"The asset {asset_id} already exists")

        owner_org = self._get_client_org_id(stub)
        asset = {
            "ID": asset_id,
            "Value": int(value),
            "Owner": owner,
            "OwnerOrg": owner_org,
        }
        await stub.put_state(asset_id, json.dumps(asset).encode())
        return pb.Response(status=ResponseCode.OK)

    async def read_asset(self, stub: ChaincodeStubInterface, asset_id: str) -> pb.Response:
        asset_bytes = await stub.get_state(asset_id)
        if not asset_bytes:
            return self._error(f"The asset {asset_id} does not exist")
        return pb.Response(status=ResponseCode.OK, payload=asset_bytes)

    async def update_asset(self, stub: ChaincodeStubInterface, asset_id: str, new_value: str) -> pb.Response:
        asset_data = await stub.get_state(asset_id)
        if not asset_data:
            return self._error(f"The asset {asset_id} does not exist")

        asset = json.loads(asset_data.decode())
        asset["Value"] = int(new_value)
        await stub.put_state(asset_id, json.dumps(asset).encode())
        return pb.Response(status=ResponseCode.OK)

    async def delete_asset(self, stub: ChaincodeStubInterface, asset_id: str) -> pb.Response:
        if not await self.asset_exists(stub, asset_id):
            return self._error(f"The asset {asset_id} does not exist")

        await stub.delete_state(asset_id)
        return pb.Response(status=ResponseCode.OK)

    async def transfer_asset(
        self,
        stub: ChaincodeStubInterface,
        asset_id: str,
        new_owner: str,
        new_owner_org: str,
    ) -> pb.Response:
        asset_data = await stub.get_state(asset_id)
        if not asset_data:
            return self._error(f"The asset {asset_id} does not exist")

        asset = json.loads(asset_data.decode())
        asset["Owner"] = new_owner
        asset["OwnerOrg"] = new_owner_org
        await stub.put_state(asset_id, json.dumps(asset).encode())

        # NOTE: The current python shim in this repository does not yet expose
        # set_state_validation_parameter, so this sample mirrors SBE fields and
        # transfer flow, but cannot apply key-level endorsement policy from code.
        return pb.Response(status=ResponseCode.OK)

    async def asset_exists(self, stub: ChaincodeStubInterface, asset_id: str) -> bool:
        data = await stub.get_state(asset_id)
        return bool(data)

    @staticmethod
    def _get_client_org_id(stub: ChaincodeStubInterface) -> str:
        creator = stub.get_creator() or {}
        mspid = creator.get("mspid") if isinstance(creator, dict) else None
        return mspid or "Org1MSP"

    @staticmethod
    def _error(msg: str) -> pb.Response:
        return pb.Response(status=ResponseCode.ERROR, message=msg)


if __name__ == "__main__":
    start(AssetTransferSBEChaincode())
