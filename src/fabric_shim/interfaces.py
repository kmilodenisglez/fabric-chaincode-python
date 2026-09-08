# Copyright the Institute of Cryptography, Faculty of Mathematics and Computer Science at University of Havana
# contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod

from fabric_protos_python.peer import proposal_response_pb2 as pb


class ChaincodeStubInterface(ABC):
    """
    ChaincodeStubInterface is used by deployable chaincode apps to access and modify their ledgers
    """
    def get_function_and_parameters(self):  # Get the chaincode calling method name and parameter list
        pass

    def get_txid(self):  # Get the ID of the chaincode calling transaction
        pass

    def get_channel_id(self):  # Get the channel ID of the chaincode calling transaction
        pass

    def get_creator(self):  # Get the user ID of the chaincode calling transaction
        pass

    def get_transient(self):  # Get the transient dataset of chaincode call transactions
        pass

    def get_tx_timestamp(self):  # Get the timestamp of the chaincode calling transaction
        pass

    @abstractmethod
    def get_state(self, key: str): #-> bytearray:
        """
            GetState returns the value of the specified `key` from the
            ledger. Note that GetState doesn't read data from the writeset, which
            has not been committed to the ledger. In other words, GetState doesn't
            consider data modified by PutState that has not been committed.
            If the key does not exist in the state database, (nil, nil) is returned.
        """

    def put_state(self, key: str, value):  # update the state of the specified key on the ledger
        pass

    def delete_state(self, key: str):  # delete the state of the specified key on the ledger
        pass

    def set_state_validation_parameter(self):  # Set state validation parameters
        pass

    def get_state_validation_parameter(self):  # Get state validation parameters
        pass

    def get_state_by_range(self):  # Get the state of the keys in the specified range on the ledger
        pass

    def get_state_by_range_with_pagination(
            self):  # Pagination to get the state of the keys in the specified range on the ledger
        pass

    def get_query_result(self):  # Get the node rich query result, which is only valid when couchdb is used
        pass

    def get_query_result_with_pagination(self):  # Pagination to get node rich query results
        pass

    def get_history_for_key(self):  # Get the update history of the specified key on the ledger
        pass

    def invoke_chaincode(self):  # Invoke other chaincodes
        pass

    def set_event(self):  # trigger chaincode event
        pass

    def create_composite_key(self):  # Create a composite key
        pass

    # split composite key, return composite key type and composition attribute value
    def split_composite_key(self):
        pass

    def get_state_by_partial_composite_key(self):  # Query the ledger state using a partial composite key
        pass

    # Use partial composite key pagination to query ledger state
    def get_state_by_partial_composite_key_with_pagination(self):
        pass

    def get_private_data(self):  # Get the status of the specified key in the specified private dataset
        pass

    def get_private_data_hash(self):  # Get the state hash of the specified key in the specified private dataset
        pass

    def put_private_data(self):  # Update the state of the specified key in the specified private dataset
        pass

    def delete_private_data(self):  # delete the specified key in the specified private data set
        pass

    def set_private_data_validation_parameter(self):  # Set validation parameters for private data
        pass

    def get_private_data_validation_parameter(self):  # Get the validation parameters for private data
        pass

    # Get the status of the keys of the specified range in the specified private dataset
    def get_private_data_by_range(self):
        pass

    def get_private_data_by_partial_composite_key(self):  # Query a private dataset with a partial composite key
        pass

    # Get rich query results for private datasets, only valid when couchdb is enabled
    def get_private_data_query_result(self):
        pass


class Chaincode(ABC):
    @staticmethod
    @abstractmethod
    async def init(stub: ChaincodeStubInterface) -> pb.Response:
        """
        init is called during Instantiate transaction after the chaincode container has been established for the
        first time, allowing the chaincode to initialize its internal data
        """
        pass

    @staticmethod
    @abstractmethod
    async def invoke(stub: ChaincodeStubInterface) -> pb.Response:
        """
        invoke is called to update or query the ledger in a proposal transaction. Updated state variables are not
        committed to the ledger until the transaction is committed.
        """
        pass
