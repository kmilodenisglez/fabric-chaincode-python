import asyncio
import os
import sys

# Ensure local package fabric_protos_python under fabric-chaincode-python is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fabric_protos_python.peer import chaincode_shim_pb2 as ccshim_pb2
from fabric_protos_python.peer import chaincode_pb2 as cc_pb2
from fabric_protos_python.peer import proposal_response_pb2 as pr_pb

from src.fabric_shim.handler import Handler
from src.fabric_shim.interfaces import Chaincode


class TestChaincode(Chaincode):
    async def init(self, stub):
        return pr_pb.Response(status=200)

    async def invoke(self, stub):
        return pr_pb.Response(status=200, message=b'OK')


class FakeContext:
    def __init__(self):
        self.written = []

    async def write(self, msg):
        # record the messages chaincode writes back to peer
        self.written.append(msg)


async def message_stream():
    # Peer responds to REGISTER with REGISTERED
    yield ccshim_pb2.ChaincodeMessage(type=ccshim_pb2.ChaincodeMessage.REGISTERED)
    # Peer sends READY
    yield ccshim_pb2.ChaincodeMessage(type=ccshim_pb2.ChaincodeMessage.READY)

    # Peer sends a TRANSACTION with a simple ChaincodeInput
    cc_input = cc_pb2.ChaincodeInput()
    cc_input.args.append(b'NoOp')
    txmsg = ccshim_pb2.ChaincodeMessage(
        type=ccshim_pb2.ChaincodeMessage.TRANSACTION,
        payload=cc_input.SerializeToString(),
        txid='tx1',
        channel_id='ch1'
    )
    yield txmsg


async def run_test():
    handler = Handler('testcc', TestChaincode())
    fake_context = FakeContext()

    await handler.chat_with_peer(message_stream(), fake_context)
    # allow background tasks to complete
    await asyncio.sleep(0.1)

    # ensure that chaincode wrote at least the REGISTER and the COMPLETED message
    types = [m.type for m in fake_context.written]
    print('written types:', types)

    assert any(t == ccshim_pb2.ChaincodeMessage.COMPLETED for t in types), 'No COMPLETED message found'
    print('Test OK')


if __name__ == '__main__':
    asyncio.run(run_test())
