import asyncio
import os
import sys

import pytest

# Ensure project package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fabric_protos_python.peer import chaincode_shim_pb2 as ccshim_pb2
from fabric_protos_python.peer import chaincode_pb2 as cc_pb2
from fabric_protos_python.peer import proposal_response_pb2 as pr_pb

from src.fabric_shim.handler import Handler
from src.fabric_shim.interfaces import Chaincode


class FakeContext:
    def __init__(self):
        self.written = []
        self.handler = None

    async def write(self, msg):
        # record messages written by the chaincode runtime
        self.written.append(msg)

        # simulate peer responses for GET/PUT/DEL operations
        try:
            mtype = msg.type
        except Exception:
            return

        if mtype == ccshim_pb2.ChaincodeMessage.GET_STATE:
            # reply with empty payload (not found)
            resp = ccshim_pb2.ChaincodeMessage(
                type=ccshim_pb2.ChaincodeMessage.RESPONSE,
                payload=b'',
                txid=msg.txid,
                channel_id=msg.channel_id,
            )
            asyncio.create_task(self.handler.handle_message(resp))
        elif mtype == ccshim_pb2.ChaincodeMessage.PUT_STATE:
            resp = ccshim_pb2.ChaincodeMessage(
                type=ccshim_pb2.ChaincodeMessage.RESPONSE,
                payload=b'OK',
                txid=msg.txid,
                channel_id=msg.channel_id,
            )
            asyncio.create_task(self.handler.handle_message(resp))


async def message_stream_for_tx(func_name, args=None, txid='tx1', channel='ch1'):
    # Peer: send REGISTERED
    yield ccshim_pb2.ChaincodeMessage(type=ccshim_pb2.ChaincodeMessage.REGISTERED)
    # Peer: send READY
    yield ccshim_pb2.ChaincodeMessage(type=ccshim_pb2.ChaincodeMessage.READY)

    # Build ChaincodeInput payload
    cc_input = cc_pb2.ChaincodeInput()
    cc_input.args.append(func_name.encode() if isinstance(func_name, str) else func_name)
    if args:
        for a in args:
            cc_input.args.append(a.encode() if isinstance(a, str) else a)

    yield ccshim_pb2.ChaincodeMessage(
        type=ccshim_pb2.ChaincodeMessage.TRANSACTION,
        payload=cc_input.SerializeToString(),
        txid=txid,
        channel_id=channel,
    )


class TestChaincode(Chaincode):
    async def init(self, stub):
        return pr_pb.Response(status=200)

    async def invoke(self, stub):
        return pr_pb.Response(status=200, message=b'OK')


class GetPutChaincode(Chaincode):
    async def init(self, stub):
        return pr_pb.Response(status=200)

    async def invoke(self, stub):
        func, params = stub.get_function_and_parameters()
        if func == 'GetPut':
            key = params[0]
            val = params[1]
            existing = await stub.get_state(key)
            # store new value regardless (simple behavior)
            await stub.put_state(key, val)
            return pr_pb.Response(status=200)
        return pr_pb.Response(status=400)


@pytest.mark.asyncio
async def test_invoke_completed():
    handler = Handler('testcc', TestChaincode())
    fake_context = FakeContext()
    fake_context.handler = handler

    await handler.chat_with_peer(message_stream_for_tx('NoOp', []), fake_context)
    await asyncio.sleep(0.05)

    types = [m.type for m in fake_context.written]
    assert ccshim_pb2.ChaincodeMessage.COMPLETED in types


@pytest.mark.asyncio
async def test_get_put_flow():
    handler = Handler('testcc', GetPutChaincode())
    fake_context = FakeContext()
    fake_context.handler = handler

    await handler.chat_with_peer(message_stream_for_tx('GetPut', ['k1', 'v1']), fake_context)
    await asyncio.sleep(0.05)

    types = [m.type for m in fake_context.written]

    assert ccshim_pb2.ChaincodeMessage.GET_STATE in types
    assert ccshim_pb2.ChaincodeMessage.PUT_STATE in types
    assert ccshim_pb2.ChaincodeMessage.COMPLETED in types
