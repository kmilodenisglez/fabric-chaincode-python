# handler.py

# Copyright the Institute of Cryptography, Faculty of Mathematics and Computer Science at University of Havana
# contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# ChaincodeSupportClient Class

# The main API list of ChaincodeSupportClient is as follows:
#
#      chat_with_peer(): Starts a two-way communication flow with the peer node

import datetime
from typing import AsyncIterable
import asyncio
import grpc

from fabric_protos_python.peer import chaincode_shim_pb2 as ccshim_pb2
from fabric_protos_python.peer import chaincode_pb2 as cc_pb2
from fabric_protos_python.peer import proposal_response_pb2 as pr_pb
from src.fabric_shim.stub import ChaincodeStub
from src.fabric_shim.msg_queue_handler import MsgQueueHandler, QueueMessage
from src.fabric_shim.response import new_error_msg, ResponseCode
from src.fabric_shim.utils import generate_logging_prefix
from src.fabric_shim.logging import LOGGER
from src.fabric_shim.interfaces import Chaincode


class STATES:
    CREATED = "created"  # start state
    ESTABLISHED = "established"  # connection established
    READY = "ready"  # ready for requests


MIN_UNICODE_RUNE_VALUE = '\u0000'  # U + 0000
MAX_UNICODE_RUNE_VALUE = '\u0010FFFF'  # U+10FFFF - maximum (and unallocated) code point
COMPOSITEKEY_NS = '\x00'
EMPTY_KEY_SUBSTITUTE = '\x01'

STATE = STATES.CREATED


class Handler:
    def __init__(self, cc_id: str, cc: Chaincode) -> None:
        self.chaincode_id = cc_pb2.ChaincodeID()
        self.chaincode_id.name = cc_id
        self.chaincode = cc
        self.msg_queue_handler = None
        self.context = None

    async def handle_stub_interaction(self, msg, action="Invoke"):
        """handle_message calls the Init | Invoke function of the associated chaincode."""
        # Get the function and args from Payload
        cc_input = cc_pb2.ChaincodeInput()
        cc_input.ParseFromString(msg.payload)
        
        stub = ChaincodeStub(self, msg.channel_id, msg.txid, cc_input, msg.proposal)

        # Normalize action and call appropriate chaincode method
        action_normalized = (action or "").lower()
        if action_normalized == 'init':
            method = 'Init'
            resp: pr_pb.Response = await self.chaincode.init(stub)
        else:
            method = 'Invoke'
            resp: pr_pb.Response = await self.chaincode.invoke(stub)

        # check that a response object has been returned otherwise assume an error.

        if not resp or not resp.status:
            err_msg = '%s Calling chaincode %s() has not called success or error.' \
                      % (generate_logging_prefix(msg.channel_id, msg.txid), method)
            LOGGER.info(err_msg)

            resp = pr_pb.Response(
                status=ResponseCode.ERROR,
                message=err_msg
            )

        LOGGER.info('%s Calling chaincode %s(), response status: %s'
                    % (generate_logging_prefix(msg.channel_id, msg.txid), method, resp.status))

        if resp.status >= ResponseCode.ERROR:
            err_msg = '%s Calling chaincode %s() returned error response [%s]. Sending COMPLETED message back to peer' \
                      % (generate_logging_prefix(msg.channel_id, msg.txid), method, resp.message)
            LOGGER.info(err_msg)

            next_state_msg = ccshim_pb2.ChaincodeMessage(
                type=ccshim_pb2.ChaincodeMessage.COMPLETED,
                payload=resp.SerializeToString(),
                txid=msg.txid,
                channel_id=msg.channel_id
            )
        else:
            LOGGER.info('%s Calling chaincode %s() succeeded. Sending COMPLETED message back to peer'
                        % (generate_logging_prefix(msg.channel_id, msg.txid), method))

            next_state_msg = ccshim_pb2.ChaincodeMessage(
                type=ccshim_pb2.ChaincodeMessage.COMPLETED,
                payload=resp.SerializeToString(),
                txid=msg.txid,
                channel_id=msg.channel_id
            )

        await self.context.write(next_state_msg)

    async def handle_message_ready(self, msg):
        """handle_message_ready handles messages received from the peer when the handler is in the "ready" state."""
        if msg.type == ccshim_pb2.ChaincodeMessage.RESPONSE or msg.type == ccshim_pb2.ChaincodeMessage.ERROR:
            LOGGER.info("+++ ERROR or RESPONSE +++")
            await self.msg_queue_handler.handle_msg_response(msg)
        elif msg.type == ccshim_pb2.ChaincodeMessage.INIT:
            LOGGER.info("+++ call INIT +++")
            await self.handle_stub_interaction(msg, "Init")
            return
        elif msg.type == ccshim_pb2.ChaincodeMessage.TRANSACTION:
            LOGGER.info("+++ call INVOKE +++")
            await self.handle_stub_interaction(msg, "Invoke")
            return
        else:
            self.context.write(new_error_msg(msg, STATE))

    def handle_message_established(self, msg):
        """
        handle_message_established handles messages received from the peer when the handler is in the "established" state.
        """
        global STATE
        if msg.type != ccshim_pb2.ChaincodeMessage.READY:
            LOGGER.error(f'Chaincode is in "established" state, can only process messages of type "ready", '
                         f'but received "{msg.type}"')
            # write is an async coroutine on the context
            try:
                return asyncio.create_task(self.context.write(new_error_msg(msg, STATE)))
            except Exception:
                return
        else:
            LOGGER.info('Successfully established communication with peer node. State transferred to "ready"')
            STATE = STATES.READY

    def handle_message_created(self, msg):
        """handle_message_created handles messages received from the peer when the handler is in the "created" state."""
        global STATE
        if msg.type != ccshim_pb2.ChaincodeMessage.REGISTERED:
            LOGGER.error(f'Chaincode is in "created" state, can only process messages of type "registered", '
                         f'but received "{msg.type}"')
            try:
                return asyncio.create_task(self.context.write(new_error_msg(msg, STATE)))
            except Exception:
                return
        else:
            LOGGER.info('Successfully registered with peer node. State transferred to "established"')
            STATE = STATES.ESTABLISHED

    async def handle_message(self, msg: ccshim_pb2.ChaincodeMessage):
        """handle_message message handles loop for shim side of chaincode/peer stream."""
        LOGGER.warning('-->> Look out!')
        global STATE

        # TODO: ?
        if msg.type == ccshim_pb2.ChaincodeMessage.KEEPALIVE:
            LOGGER.info('-| KEEPALIVE')
            return

        if STATE == STATES.READY:
            await self.handle_message_ready(msg)
        elif STATE == STATES.ESTABLISHED:
            self.handle_message_established(msg)
        elif STATE == STATES.CREATED:
            self.handle_message_created(msg)
        else:
            try:
                asyncio.create_task(self.context.write(new_error_msg(msg, STATE)))
            except Exception:
                LOGGER.exception('Failed to write error message to context')

    async def chat_with_peer(self, stream: AsyncIterable[ccshim_pb2.ChaincodeMessage], context: grpc.aio.ServicerContext):
        """chat stream for peer-chaincode interactions post connection"""
        global STATE
        STATE = STATES.CREATED

        self.context = context
        self.msg_queue_handler = MsgQueueHandler(self)

        # Send the ChaincodeID during register.
        cm = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.REGISTER, payload=self.chaincode_id.SerializeToString())
        cm.timestamp.FromDatetime(datetime.datetime.now())

        # Register on the stream
        await self.context.write(cm)

        async for receive_message in stream:
            LOGGER.info('Received message')
            if receive_message is None:
                err_str = "received nil message, ending chaincode stream"
                LOGGER.error(err_str)
                return ccshim_pb2.ChaincodeMessage(
                    type=ccshim_pb2.ChaincodeMessage.ERROR, payload=err_str.encode(encoding='utf-8'))
            else:
                asyncio.create_task(self.handle_message(receive_message))

                LOGGER.info(f'->>>>  proposal  {receive_message.proposal}')
                LOGGER.info(f'->>>>  payload  {receive_message.payload}')
                LOGGER.info(f'->>>>  channel ID  {receive_message.channel_id}')
                LOGGER.info(f'->>>>  Tx ID  {receive_message.txid}')

    async def handle_get_state(self, collection, key, channel_id, tx_id):
        msg_pb = ccshim_pb2.GetState()
        msg_pb.key = key
        msg_pb.collection = collection
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.GET_STATE,
            payload=msg_pb.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id
        )

        result = await self.__ask_peer_and_listen(msg, 'GetState')
        return result.payload
    
    async def handle_put_state(self, collection, key, value, channel_id, tx_id):
        msg_pb = ccshim_pb2.PutState()
        msg_pb.key = key
        msg_pb.value = value
        msg_pb.collection = collection
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.PUT_STATE,
            payload=msg_pb.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id
        )
        return await self.__ask_peer_and_listen(msg, 'PutState')

    async def handle_delete_state(self, collection, key, channel_id, tx_id):
        msg_pb = ccshim_pb2.DelState()
        msg_pb.key = key
        msg_pb.collection = collection
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.DEL_STATE,
            payload=msg_pb.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id
        )
        return await self.__ask_peer_and_listen(msg, 'DeleteState')
    
    async def __ask_peer_and_listen(self, msg, action):
        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        message = QueueMessage(msg, action, fut)
        await self.msg_queue_handler.queue_msg(message)

        return await fut
