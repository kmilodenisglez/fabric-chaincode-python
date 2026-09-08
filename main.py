from ctypes import c_char

from src.fabric_shim.interfaces import Chaincode, ChaincodeStubInterface
from src.fabric_shim.server import start
from src.fabric_shim.response import ResponseCode

import json
from fabric_protos_python.peer import proposal_response_pb2 as pb

# HOST = '127.0.0.1'
# PORT = 9999
# address_str: str = f"{HOST}:{PORT}"
# cc_id: str = "basic_1.0:6f953644cba819469faf754a24e6a839b3065703a0e55d559e419de3c6361a9d"


class Asset:
    def __init__(self, id_=None, color=None, size=None, owner=None, appraised_value=None):
        self.id: str = id_
        self.color: str = color
        self.size: int = size
        self.owner: str = owner
        self.appraised_value: int = appraised_value


class MyChaincode(Chaincode):
    async def init(self, stub: ChaincodeStubInterface) -> pb.Response:
        await self.init_ledger(self, stub)
        return pb.Response(status=ResponseCode.OK)

    async def invoke(self, stub: ChaincodeStubInterface) -> pb.Response:
        action, inputs = stub.get_function_and_parameters()
        if action == "InitLedger":
            await self.init_ledger(self, stub)
            return pb.Response(status=ResponseCode.OK)
        elif action == "CreateAsset" or action == "UpdateAsset":
            new_asset = Asset(
                inputs[0],
                inputs[1],
                inputs[2],
                inputs[3],
                inputs[4])
            await self.create_asset(self, stub, new_asset)
            return pb.Response(status=ResponseCode.OK)
        elif action == "ReadAsset":
            asset_id = inputs[0]
            result: Asset = await self.read_asset(self, stub, asset_id)
            return pb.Response(status=ResponseCode.OK, message=result)
        elif action == "DeleteAsset":
            asset_id = inputs[0]
            await self.delete_state(self, stub, asset_id)
            return pb.Response(status=ResponseCode.OK)
        else:
            return pb.Response(status=ResponseCode.ERROR)

    async def init_ledger(self, stub: ChaincodeStubInterface):
        init_ledger_values = [
            Asset("asset1", "blue", 5, "Tomoko", 300),
            Asset("asset2", "red", 5, "Brad", 400),
            Asset("asset3", "green", 10, "Jin Soo", 500)
        ]

        for asset in init_ledger_values:
            await self.create_asset(self, stub, asset)

    async def create_asset(self, stub: ChaincodeStubInterface, asset: Asset):
        await stub.put_state(asset.id, json.dumps(asset.__dict__))

    async def read_asset(self, stub: ChaincodeStubInterface, key: str) -> Asset:
        return await stub.get_state(key)

    async def delete_state(self, stub: ChaincodeStubInterface, key: str):
        await stub.delete_state(key)


if __name__ == '__main__':
    mycc = MyChaincode
    start(mycc)
