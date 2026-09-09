# Copyright the Institute of Cryptography, Faculty of Mathematics and Computer Science at University of Havana
# contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
from src.fabric_shim.interfaces import ChaincodeStubInterface
from src.fabric_shim.utils import *
from fabric_protos_python.peer import chaincode_pb2 as pb
from fabric_protos_python.common import common_pb2 as cm_pb
from fabric_protos_python.peer import proposal_pb2 as pr_pb
from fabric_protos_python.msp import identities_pb2 as id_pb
from fabric_protos_python.peer import chaincode_event_pb2 as e_pb
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
