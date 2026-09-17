from src.fabric_shim.interfaces import ChaincodeStubInterface
from src.fabric_shim.utils import (
    COMPOSITEKEY_NS,
    MIN_UNICODE_RUNE_VALUE,
    validate_composite_key_attribute,
)
from fabric_protos.peer import chaincode_pb2 as pb
from fabric_protos.common import common_pb2 as cm_pb
from fabric_protos.peer import proposal_pb2 as pr_pb
from fabric_protos.msp import identities_pb2 as id_pb
from fabric_protos.peer import chaincode_event_pb2 as e_pb
from collections.abc import Sequence
from src.fabric_shim.logging import LOGGER

VALIDATION_PARAMETER: str = 'VALIDATION_PARAMETER'


class ChaincodeStub(ChaincodeStubInterface):
    """The stub encapsulates the APIs between the chaincode implementation and the Fabric peer"""

    def __init__(self, client, channel_id, tx_id, cc_input, signed_proposal_pb):
        self.client = client
        self.channel_id = channel_id
        self.tx_id = tx_id
        self.cc_input = cc_input
        self.signed_proposal_pb = signed_proposal_pb
        self.creator = {}
        self.tx_timestamp = None
        self.proposal = None
        self.validationParameterMetakey = VALIDATION_PARAMETER

        if self.signed_proposal_pb:
            # Only attempt to decode the signed proposal if it contains proposal_bytes
            proposal_bytes = getattr(self.signed_proposal_pb, 'proposal_bytes', None)
            if proposal_bytes:
                decoded_sp = {
                    'signature': getattr(self.signed_proposal_pb, 'signature', None)
                }
                proposal = pr_pb.Proposal.FromString(proposal_bytes)
                decoded_sp['proposal'] = {}
                self.proposal = proposal

                if not proposal.header or len(proposal.header) == 0:
                    raise Exception('Proposal header is empty')

                if not proposal.payload or len(proposal.payload) == 0:
                    raise Exception('Proposal payload is empty')

                try:
                    header = cm_pb.Header.FromString(proposal.header)
                    # Use a dict for the decoded header fields rather than assigning
                    # the protobuf Header object directly (protobuf objects don't
                    # support item assignment). Keep the parsed `header` protobuf
                    # in a local variable for further extraction.
                    decoded_sp['proposal']['header'] = {}
                    decoded_sp['proposal']['header']['_raw_header'] = header
                except Exception as e:
                    raise Exception('Could not extract the header from the proposal: ' + str(e))

                try:
                    signature_header = cm_pb.SignatureHeader.FromString(header.signature_header)
                    decoded_sp['proposal']['header']['signatureHeader'] = \
                        {'nonce': signature_header.nonce, 'creator_u8': signature_header.creator}
                except Exception as e:
                    raise Exception('Decoding SignatureHeader failed: ' + str(e))

                try:
                    creator = id_pb.SerializedIdentity.FromString(signature_header.creator)
                    decoded_sp['proposal']['header']['signatureHeader']['creator'] = creator
                    self.creator = {'mspid': creator.mspid, 'idBytes': creator.id_bytes}
                except Exception as e:
                    raise Exception('Decoding SerializedIdentity failed: ' + str(e))

                try:
                    channel_header = cm_pb.ChannelHeader.FromString(header.channel_header)
                    decoded_sp['proposal']['header']['channelHeader'] = channel_header
                    self.tx_timestamp = channel_header.timestamp
                except Exception as e:
                    raise Exception('Decoding ChannelHeader failed: ' + str(e))

                try:
                    ccpp = pr_pb.ChaincodeProposalPayload.FromString(proposal.payload)
                    decoded_sp['proposal']['payload'] = ccpp
                except Exception as e:
                    raise Exception('Decoding ChaincodeProposalPayload failed: %s' + str(e))

                self.signed_proposal_pb = decoded_sp
            else:
                # No proposal bytes provided; treat as unsigned/no proposal for tests
                self.signed_proposal_pb = None

    def get_channel_id(self):
        """Get the channel ID of the chaincode calling transaction"""
        return self.channel_id

    def get_tx_timestamp(self):
        """Get the timestamp of the chaincode calling transaction"""
        return self.tx_timestamp

    def get_creator(self):
        """Get the user ID of the chaincode calling transaction"""
        return self.creator

    def get_txid(self):
        """Get the ID of the chaincode calling transaction"""
        return self.tx_id

    def get_function_and_parameters(self):
        """Get function name and parameters of the chaincode calling transaction"""
        args = [arg.decode() for arg in self.cc_input.args]
        if len(args) == 0:
            raise Exception('no function name provided in transaction payload')
        function: str = args[0]
        params = args[1:]

        return function, params

    async def get_state(self, key: str): #-> bytearray:
        """Get asset state from ledger"""
        LOGGER.info('get_state called with key:%s' % key)
        # Access public data by setting the collection to empty string
        collection = ''
        return await self.client.handle_get_state(collection, key, self.channel_id, self.tx_id)

    async def put_state(self, key: str, value):
        """Put asset state to ledger"""
        LOGGER.info('put_state called with key:%s and value:%s' % (key, value))
        # Access public data by setting the collection to empty string
        collection = ''
        if isinstance(value, str):
            value = bytes(value.encode())
        return await self.client.handle_put_state(collection, key, value, self.channel_id, self.tx_id)

    async def delete_state(self, key: str):
        """Delete asset state from ledger"""
        LOGGER.info('delete_state called with key:%s' % key)
        # Access public data by setting the collection to empty string
        collection = ''
        return await self.client.handle_delete_state(collection, key, self.channel_id, self.tx_id)

    async def get_state_by_range(self, start_key: str, end_key: str):
        """Returns a range of keys from the ledger.

        Returns an async iterator yielding :class:`KV` records (with
        ``key`` and ``value`` byte fields).  Both keys may be empty strings
        to mean "unbounded".
        """
        collection = ''
        from src.fabric_shim.iterators import StateQueryIterator
        from fabric_protos.peer import chaincode_shim_pb2 as ccshim_pb2
        from fabric_protos.ledger.queryresult import kv_query_result_pb2 as kv_pb

        raw = await self.client.handle_get_state_by_range(
            collection, start_key, end_key,
            self.channel_id, self.tx_id,
        )
        return StateQueryIterator(
            handler=self.client,
            channel_id=self.channel_id,
            tx_id=self.tx_id,
            initial_response=raw,
            response_factory=lambda payload: ccshim_pb2.QueryResponse.FromString(payload),
            parser=lambda qrb: kv_pb.KV.FromString(qrb.result_bytes),
        )

    async def get_state_by_range_with_pagination(self, start_key: str, end_key: str,
                                                   page_size: int, bookmark: str = ""):
        """Paginated version of :meth:`get_state_by_range`.

        Returns an async iterator yielding :class:`KV` records.  Use the
        :meth:`aclose` method of the iterator when you want to stop early.
        """
        collection = ''
        from src.fabric_shim.iterators import StateQueryIterator
        from fabric_protos.peer import chaincode_shim_pb2 as ccshim_pb2
        from fabric_protos.ledger.queryresult import kv_query_result_pb2 as kv_pb

        meta = ccshim_pb2.QueryMetadata()
        meta.pagesize = int(page_size)
        meta.bookmark = bookmark or ""
        raw = await self.client.handle_get_state_by_range(
            collection, start_key, end_key,
            self.channel_id, self.tx_id, metadata=meta.SerializeToString(),
        )
        return StateQueryIterator(
            handler=self.client,
            channel_id=self.channel_id,
            tx_id=self.tx_id,
            initial_response=raw,
            response_factory=lambda payload: ccshim_pb2.QueryResponse.FromString(payload),
            parser=lambda qrb: kv_pb.KV.FromString(qrb.result_bytes),
        )

    async def get_query_result(self, query: str):
        """Run a CouchDB rich query against the world state.

        Returns an async iterator yielding :class:`KV` records.
        """
        collection = ''
        from src.fabric_shim.iterators import QueryResultIterator
        from fabric_protos.peer import chaincode_shim_pb2 as ccshim_pb2
        from fabric_protos.ledger.queryresult import kv_query_result_pb2 as kv_pb

        raw = await self.client.handle_get_query_result(
            collection, query, self.channel_id, self.tx_id,
        )
        return QueryResultIterator(
            handler=self.client,
            channel_id=self.channel_id,
            tx_id=self.tx_id,
            initial_response=raw,
            response_factory=lambda payload: ccshim_pb2.QueryResponse.FromString(payload),
            parser=lambda qrb: kv_pb.KV.FromString(qrb.result_bytes),
        )

    async def get_query_result_with_pagination(self, query: str, page_size: int,
                                                bookmark: str = ""):
        """Paginated version of :meth:`get_query_result`."""
        collection = ''
        from src.fabric_shim.iterators import QueryResultIterator
        from fabric_protos.peer import chaincode_shim_pb2 as ccshim_pb2
        from fabric_protos.ledger.queryresult import kv_query_result_pb2 as kv_pb

        meta = ccshim_pb2.QueryMetadata()
        meta.pagesize = int(page_size)
        meta.bookmark = bookmark or ""
        raw = await self.client.handle_get_query_result(
            collection, query, self.channel_id, self.tx_id,
            metadata=meta.SerializeToString(),
        )
        return QueryResultIterator(
            handler=self.client,
            channel_id=self.channel_id,
            tx_id=self.tx_id,
            initial_response=raw,
            response_factory=lambda payload: ccshim_pb2.QueryResponse.FromString(payload),
            parser=lambda qrb: kv_pb.KV.FromString(qrb.result_bytes),
        )

    async def get_history_for_key(self, key: str):
        """Return the history of modifications for *key*.

        Yields :class:`KeyModification` records (``tx_id``, ``value``,
        ``timestamp``, ``is_delete``).
        """
        from src.fabric_shim.iterators import HistoryQueryIterator
        from fabric_protos.peer import chaincode_shim_pb2 as ccshim_pb2
        from fabric_protos.ledger.queryresult import kv_query_result_pb2 as kv_pb

        raw = await self.client.handle_get_history_for_key(
            key, self.channel_id, self.tx_id,
        )
        return HistoryQueryIterator(
            handler=self.client,
            channel_id=self.channel_id,
            tx_id=self.tx_id,
            initial_response=raw,
            response_factory=lambda payload: ccshim_pb2.QueryResponse.FromString(payload),
            parser=lambda qrb: kv_pb.KeyModification.FromString(qrb.result_bytes),
        )

    async def get_state_by_partial_composite_key(self, object_type: str,
                                                   attributes):
        """Range query on the ledger using a partial composite key.

        Builds a composite key prefix from *object_type* and *attributes*
        and runs a range query from that prefix to the next code point.
        """
        full_key = self.create_composite_key(object_type, attributes)
        # Range from the composite key to the same prefix with the maximum
        # rune appended — this is the Fabric convention for "prefix" range
        # queries against composite keys.
        end_key = full_key + '\U0010FFFF'
        return await self.get_state_by_range(full_key, end_key)

    async def invoke_chaincode(self, chaincode_name: str, args, channel: str = ""):
        """Invoke another chaincode by name.

        ``args`` is a list of strings (or bytes).  The return value is the
        ``Response`` produced by the invoked chaincode.
        """
        from fabric_protos.peer import proposal_response_pb2 as pr_pb
        # If a channel is supplied, build a fully-qualified name.
        fully_qualified = f"{chaincode_name}/{channel}" if channel else chaincode_name
        raw = await self.client.handle_invoke_chaincode(
            fully_qualified, list(args), self.channel_id, self.tx_id,
        )
        # raw.payload is a serialised proposal Response
        return pr_pb.Response.FromString(raw.payload)

    def set_event(self, name: str, payload):
        """Emit a chaincode event.

        ``payload`` is stored on the stub and serialised into the final
        ``COMPLETED`` message built by the handler.
        """
        if not isinstance(name, str) or not name:
            raise Exception('event name must be a non-empty string')
        if isinstance(payload, str):
            payload = payload.encode()
        elif payload is None:
            payload = b''
        # Lazily initialise the event list on the stub.
        if not hasattr(self, '_events') or self._events is None:
            self._events = []
        from fabric_protos.peer import chaincode_event_pb2 as e_pb
        evt = e_pb.ChaincodeEvent()
        evt.chaincode_id = self.chaincode_id_name if hasattr(self, 'chaincode_id_name') else ""
        evt.tx_id = self.tx_id
        evt.event_name = name
        evt.payload = bytes(payload)
        self._events.append(evt)

    def get_events(self):
        """Internal: return the list of accumulated events (used by handler)."""
        return list(getattr(self, '_events', []) or [])

    def create_composite_key(self, object_type, attributes):
        """Creates a composite key by combining the objectType string
        and the given `attributes` to form a composite key"""
        validate_composite_key_attribute(object_type)
        if not isinstance(attributes, Sequence):
            raise Exception('attributes must be an array')

        composite_key = COMPOSITEKEY_NS + object_type + MIN_UNICODE_RUNE_VALUE
        for attribute in attributes:
            validate_composite_key_attribute(attribute)
            composite_key = composite_key + attribute + MIN_UNICODE_RUNE_VALUE
        return composite_key

    def split_composite_key(self, composite_key):
        object_type = None
        attributes = []
        if composite_key and len(composite_key) > 1 and composite_key[0] == COMPOSITEKEY_NS:
            split_key = composite_key[1:].split(MIN_UNICODE_RUNE_VALUE)
            object_type = split_key[0]
            split_key.pop()
            if len(split_key) > 1:
                split_key.pop(0)
                attributes = split_key
        return object_type, attributes
