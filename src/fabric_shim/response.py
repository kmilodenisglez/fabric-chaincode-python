# Copyright the Institute of Cryptography, Faculty of Mathematics and Computer Science at University of Havana
# contributors. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
from fabric_protos_python.peer import chaincode_shim_pb2 as ccshim_pb2
from fabric_protos_python.peer import proposal_response_pb2 as pb


class ResponseCode:
    """
    OK constant - status code less than 400, endorser will endorse it.
    OK means init or invoke successfully.

    ERRORTHRESHOLD constant - status code greater than or equal to 400 will be considered an error and rejected by
    endorser.

    ERROR constant - default error value
    """
    OK, ERRORTHRESHOLD, ERROR = 200, 400, 500


def new_error_msg(msg, state) -> ccshim_pb2.ChaincodeMessage:
    err_str = f"[{msg.txid}] Chaincode h cannot handle message ({msg.type}) while in state: {state}"
    return ccshim_pb2.ChaincodeMessage(type=ccshim_pb2.ChaincodeMessage.ERROR,
                                       payload=err_str.encode(encoding='utf-8'), txid=msg.txid)


def success(payload: bytes):
    return pb.Response(status=ResponseCode.OK, message=payload)


def error():
    return pb.Response(status=ResponseCode.ERROR)
