from fabric_protos.peer import chaincode_shim_pb2 as ccshim_pb2
from fabric_protos.peer import proposal_response_pb2 as pb


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


def success(payload):
    """Build a successful Fabric Response.

    Puts *payload* in the ``payload`` (bytes) field of the Response — this
    is the field that ``peer chaincode query`` / ``invoke`` reads to print
    the chaincode result.  ``payload`` may be ``bytes``, ``str`` (will be
    UTF-8 encoded) or ``None`` (treated as an empty payload).
    """
    if payload is None:
        payload = b""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    elif isinstance(payload, bytearray):
        payload = bytes(payload)
    return pb.Response(status=ResponseCode.OK, payload=payload)


def error(message: str = ""):
    """Build an error Fabric Response.

    Puts *message* in the ``message`` (string) field of the Response — this
    is what ``peer chaincode query`` / ``invoke`` prints to stderr when
    the chaincode returns an error.
    """
    return pb.Response(status=ResponseCode.ERROR, message=message)
