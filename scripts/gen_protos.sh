#!/usr/bin/env bash
set -euo pipefail

# Generates python grpc/protobuf bindings from hyperledger/fabric-protos.
# By default uses the repository submodule at protos/fabric-protos (branch/tag v2.5.0)
# Requires: python3 -m pip install grpcio-tools

PROTO_RELEASE="v2.5.0"
# Default output directory (top-level package) so imports like
# `from fabric_protos_python.peer import chaincode_shim_pb2` work.
OUT_DIR="${OUT_DIR:-$PWD/fabric_protos_python}"

# Allow overriding the source proto path (useful for local copies or CI)
PROTO_SRC="${PROTO_SRC:-protos/fabric-protos}"

if [ -d "$PROTO_SRC" ]; then
    echo "Using existing proto sources in $PROTO_SRC"
    SRC_DIR="$PROTO_SRC"
else
    echo "Proto source not found at $PROTO_SRC, cloning fabric-protos $PROTO_RELEASE"
    TMP_DIR="/tmp/fabric-protos-$PROTO_RELEASE"
    rm -rf "$TMP_DIR"
    git clone --depth 1 --branch "$PROTO_RELEASE" https://github.com/hyperledger/fabric-protos.git "$TMP_DIR"
    SRC_DIR="$TMP_DIR"
fi

mkdir -p "$OUT_DIR"

echo "Generating python protos into $OUT_DIR from $SRC_DIR"
python3 -m grpc_tools.protoc \
        -I"$SRC_DIR" \
        --python_out="$OUT_DIR" \
        --grpc_python_out="$OUT_DIR" \
        $(find "$SRC_DIR" -name "*.proto" | tr '\n' ' ')

echo "Protos generated in $OUT_DIR"
