#!/usr/bin/env python3
# Copyright the Institute of Cryptography, Faculty of Mathematics and Computer Science at University of Havana
# contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Basic Fabric Chaincode Example (CCAAS)

This is a simple asset management chaincode that demonstrates:
- Creating assets
- Reading assets
- Updating assets
- Deleting assets
- Initializing the ledger

Deploy this as a Chaincode-as-a-Service (CCAAS) in Fabric.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.fabric_shim.interfaces import Chaincode, ChaincodeStubInterface
from src.fabric_shim.server import start
from src.fabric_shim.response import ResponseCode
from fabric_protos_python.peer import proposal_response_pb2 as pb


class Asset:
    """Represents a simple asset with basic properties"""

    def __init__(self, id_=None, color=None, size=None, owner=None, appraised_value=None):
        self.id: str = id_
        self.color: str = color
        self.size: int = size
        self.owner: str = owner
        self.appraised_value: int = appraised_value

    def to_dict(self):
        return self.__dict__


class BasicAssetChaincode(Chaincode):
    """Implements a basic asset management chaincode"""

    async def init(self, stub: ChaincodeStubInterface) -> pb.Response:
        """Initialize the ledger with sample assets"""
        await self.init_ledger(stub)
        return pb.Response(status=ResponseCode.OK)

    async def invoke(self, stub: ChaincodeStubInterface) -> pb.Response:
        """Process invoke requests"""
        action, inputs = stub.get_function_and_parameters()

        if action == "InitLedger":
            await self.init_ledger(stub)
            return pb.Response(status=ResponseCode.OK)

        elif action == "CreateAsset" or action == "UpdateAsset":
            if len(inputs) < 5:
                return pb.Response(status=ResponseCode.ERROR, message="CreateAsset requires 5 arguments")
            new_asset = Asset(
                inputs[0],  # id
                inputs[1],  # color
                inputs[2],  # size
                inputs[3],  # owner
                inputs[4]   # appraised_value
            )
            await self.create_asset(stub, new_asset)
            return pb.Response(status=ResponseCode.OK)

        elif action == "ReadAsset":
            if len(inputs) < 1:
                return pb.Response(status=ResponseCode.ERROR, message="ReadAsset requires 1 argument")
            asset_id = inputs[0]
            result = await self.read_asset(stub, asset_id)
            return pb.Response(status=ResponseCode.OK, message=result)

        elif action == "DeleteAsset":
            if len(inputs) < 1:
                return pb.Response(status=ResponseCode.ERROR, message="DeleteAsset requires 1 argument")
            asset_id = inputs[0]
            await self.delete_state(stub, asset_id)
            return pb.Response(status=ResponseCode.OK)

        elif action == "GetAllAssets":
            results = await self.get_all_assets(stub)
            return pb.Response(status=ResponseCode.OK, message=results)

        else:
            return pb.Response(status=ResponseCode.ERROR, message=f"Unknown function: {action}")

    async def init_ledger(self, stub: ChaincodeStubInterface):
        """Initialize the ledger with sample assets"""
        init_ledger_values = [
            Asset("asset1", "blue", 5, "Tomoko", 300),
            Asset("asset2", "red", 5, "Brad", 400),
            Asset("asset3", "green", 10, "Jin Soo", 500),
            Asset("asset4", "yellow", 10, "Max", 500),
            Asset("asset5", "black", 15, "Adriana", 700),
            Asset("asset6", "purple", 8, "Michel", 600),
        ]

        for asset in init_ledger_values:
            await self.create_asset(stub, asset)

    async def create_asset(self, stub: ChaincodeStubInterface, asset: Asset):
        """Create a new asset on the ledger"""
        await stub.put_state(asset.id, json.dumps(asset.to_dict()))

    async def read_asset(self, stub: ChaincodeStubInterface, key: str):
        """Read an asset from the ledger"""
        return await stub.get_state(key)

    async def get_all_assets(self, stub: ChaincodeStubInterface):
        """Get all assets from the ledger"""
        # This is a simplified version; in production, use rich queries
        results = []
        # Note: This implementation would need iterator support for full functionality
        return json.dumps(results)

    async def delete_state(self, stub: ChaincodeStubInterface, key: str):
        """Delete an asset from the ledger"""
        await stub.delete_state(key)


if __name__ == '__main__':
    chaincode = BasicAssetChaincode()
    start(chaincode)
