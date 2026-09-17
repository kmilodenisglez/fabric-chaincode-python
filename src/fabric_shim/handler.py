import datetime
from typing import AsyncIterable
import asyncio
import grpc

from fabric_protos.peer import chaincode_shim_pb2 as ccshim_pb2
from fabric_protos.peer import chaincode_pb2 as cc_pb2
from fabric_protos.peer import proposal_response_pb2 as pr_pb
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

class Handler:
    def __init__(self, cc_id: str, cc: Chaincode) -> None:
        self.chaincode_id = cc_pb2.ChaincodeID()
        self.chaincode_id.name = cc_id
        self.chaincode = cc
        self.msg_queue_handler = None
        self.context = None
        self.state = STATES.CREATED
        self._pending_tasks = set()

    def _track_task(self, coro):
        """Schedule message handling while surfacing task failures in logs."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)

        def _done_callback(done_task):
            self._pending_tasks.discard(done_task)
            try:
                exc = done_task.exception()
            except asyncio.CancelledError:
                return
            if exc is not None:
                LOGGER.exception('Unhandled exception while processing peer message', exc_info=exc)

        task.add_done_callback(_done_callback)

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
            await self.context.write(new_error_msg(msg, self.state))

    async def handle_message_established(self, msg):
        """
        handle_message_established handles messages received from the peer when the handler is in the "established" state.
        """
        if msg.type != ccshim_pb2.ChaincodeMessage.READY:
            LOGGER.error(f'Chaincode is in "established" state, can only process messages of type "ready", '
                         f'but received "{msg.type}"')
            await self.context.write(new_error_msg(msg, self.state))
        else:
            LOGGER.info('Successfully established communication with peer node. State transferred to "ready"')
            self.state = STATES.READY

    async def handle_message_created(self, msg):
        """handle_message_created handles messages received from the peer when the handler is in the "created" state."""
        if msg.type != ccshim_pb2.ChaincodeMessage.REGISTERED:
            LOGGER.error(f'Chaincode is in "created" state, can only process messages of type "registered", '
                         f'but received "{msg.type}"')
            await self.context.write(new_error_msg(msg, self.state))
        else:
            LOGGER.info('Successfully registered with peer node. State transferred to "established"')
            self.state = STATES.ESTABLISHED

    async def handle_message(self, msg: ccshim_pb2.ChaincodeMessage):
        """handle_message message handles loop for shim side of chaincode/peer stream."""
        LOGGER.warning('-->> Look out!')

        # TODO: ?
        if msg.type == ccshim_pb2.ChaincodeMessage.KEEPALIVE:
            LOGGER.info('-| KEEPALIVE')
            return

        if self.state == STATES.READY:
            await self.handle_message_ready(msg)
        elif self.state == STATES.ESTABLISHED:
            await self.handle_message_established(msg)
        elif self.state == STATES.CREATED:
            await self.handle_message_created(msg)
        else:
            await self.context.write(new_error_msg(msg, self.state))

    async def chat_with_peer(self, stream: AsyncIterable[ccshim_pb2.ChaincodeMessage], context: grpc.aio.ServicerContext):
        """chat stream for peer-chaincode interactions post connection"""
        self.state = STATES.CREATED

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
                # Keep handling asynchronous so the stream can continue receiving
                # response frames needed by in-flight request futures.
                self._track_task(self.handle_message(receive_message))

                LOGGER.info(f'->>>>  proposal  {receive_message.proposal}')
                LOGGER.info(f'->>>>  payload  {receive_message.payload}')
                LOGGER.info(f'->>>>  channel ID  {receive_message.channel_id}')
                LOGGER.info(f'->>>>  Tx ID  {receive_message.txid}')

        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)

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

    async def handle_get_state_by_range(self, collection, start_key, end_key,
                                          channel_id, tx_id, metadata=None):
        """Send a GetStateByRange request to the peer.

        ``metadata`` (if present) is a serialised :class:`QueryMetadata`
        message — used for pagination.
        """
        msg_pb = ccshim_pb2.GetStateByRange()
        msg_pb.start_key = start_key or ""
        msg_pb.end_key = end_key or ""
        msg_pb.collection = collection
        if metadata is not None:
            msg_pb.metadata = metadata
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.GET_STATE_BY_RANGE,
            payload=msg_pb.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id,
        )
        return await self.__ask_peer_and_listen(msg, 'GetStateByRange')

    async def handle_get_query_result(self, collection, query, channel_id, tx_id,
                                       metadata=None):
        """Send a GetQueryResult (CouchDB rich query) request to the peer."""
        msg_pb = ccshim_pb2.GetQueryResult()
        msg_pb.query = query
        msg_pb.collection = collection
        if metadata is not None:
            msg_pb.metadata = metadata
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.GET_QUERY_RESULT,
            payload=msg_pb.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id,
        )
        return await self.__ask_peer_and_listen(msg, 'GetQueryResult')

    async def handle_get_history_for_key(self, key, channel_id, tx_id):
        """Send a GetHistoryForKey request to the peer."""
        msg_pb = ccshim_pb2.GetHistoryForKey()
        msg_pb.key = key
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.GET_HISTORY_FOR_KEY,
            payload=msg_pb.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id,
        )
        return await self.__ask_peer_and_listen(msg, 'GetHistoryForKey')

    async def handle_query_state_next(self, query_id, channel_id, tx_id):
        """Fetch the next page of an in-flight paged query."""
        msg_pb = ccshim_pb2.QueryStateNext()
        msg_pb.id = query_id
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.QUERY_STATE_NEXT,
            payload=msg_pb.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id,
        )
        return await self.__ask_peer_and_listen(msg, 'QueryStateNext')

    async def handle_query_state_close(self, query_id, channel_id, tx_id):
        """Close an in-flight paged query."""
        msg_pb = ccshim_pb2.QueryStateClose()
        msg_pb.id = query_id
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.QUERY_STATE_CLOSE,
            payload=msg_pb.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id,
        )
        return await self.__ask_peer_and_listen(msg, 'QueryStateClose')

    async def handle_invoke_chaincode(self, chaincode_name, args, channel_id, tx_id):
        """Invoke another chaincode by name."""
        ci = cc_pb2.ChaincodeInput()
        for a in args:
            ci.args.append(a.encode() if isinstance(a, str) else a)
        msg = ccshim_pb2.ChaincodeMessage(
            type=ccshim_pb2.ChaincodeMessage.INVOKE_CHAINCODE,
            payload=ci.SerializeToString(),
            txid=tx_id,
            channel_id=channel_id,
        )
        return await self.__ask_peer_and_listen(msg, 'InvokeChaincode')

    async def __ask_peer_and_listen(self, msg, action):
        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        message = QueueMessage(msg, action, fut)
        await self.msg_queue_handler.queue_msg(message)

        return await fut
