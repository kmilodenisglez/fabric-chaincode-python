# Basic Asset Chaincode - CCAAS Example

This directory contains a complete example of a Hyperledger Fabric Python chaincode deployed as a Chaincode-as-a-Service (CCAAS).

## Overview

This example implements a simple asset management system where you can:
- **CreateAsset** - Create a new asset with properties (id, color, size, owner, value)
- **ReadAsset** - Read an existing asset from the ledger
- **UpdateAsset** - Update an asset (same as CreateAsset)
- **DeleteAsset** - Delete an asset from the ledger
- **InitLedger** - Initialize the ledger with sample assets
- **GetAllAssets** - Retrieve all assets

## Prerequisites

- Hyperledger Fabric test network running (e.g., `test-network-nano-bash`)
- Python 3.10+ with `venv`
- Peer CLI (`peer`) configured and in PATH
- The parent `fabric-chaincode-python` repository available

## Quick Start

### 1. Prepare Python Environment

```bash
cd /path/to/fabric-chaincode-python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install "grpcio>=1.83.1"
```

### 2. Package the Chaincode

From the repository root:

```bash
mkdir -p chaincode-external/package

# Copy connection and metadata files
cp examples/ccaas-basic/connection.json chaincode-external/package/
cp examples/ccaas-basic/metadata.json chaincode-external/

# Package it
cd chaincode-external
tar -C package -czf code.tar.gz connection.json
tar -czf external-chaincode.tgz code.tar.gz metadata.json
cd ..
```

### 3. Install on Peer

```bash
cd /path/to/test-network-nano-bash
. ./peer1admin.sh

PKG=/path/to/fabric-chaincode-python/chaincode-external/external-chaincode.tgz
peer lifecycle chaincode install "$PKG"
```

### 4. Approve & Commit

```bash
PACKAGE_ID="<output-from-install-command>"

peer lifecycle chaincode approveformyorg \
  -o 127.0.0.1:6050 \
  --channelID mychannel \
  --name basic \
  --version 1 \
  --package-id "$PACKAGE_ID" \
  --sequence 1 \
  --tls \
  --cafile "$PWD/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt"

peer lifecycle chaincode commit \
  -o 127.0.0.1:6050 \
  --channelID mychannel \
  --name basic \
  --version 1 \
  --sequence 1 \
  --tls \
  --cafile "$PWD/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt"
```

### 5. Start the Chaincode Server

```bash
cd /path/to/fabric-chaincode-python
source .venv/bin/activate

# Get the installed package ID
cd /path/to/test-network-nano-bash
. ./peer1admin.sh
PACKAGE_ID=$(peer lifecycle chaincode queryinstalled --output json | \
  jq -r '.installed_chaincodes[] | select(.references.mychannel? != null) | \
  select(.references.mychannel.chaincodes[]? .name=="basic") | .package_id')

# Start the server
cd /path/to/fabric-chaincode-python
export CHAINCODE_ID="$PACKAGE_ID"
export CHAINCODE_SERVER_ADDRESS=127.0.0.1:9999
python examples/ccaas-basic/main.py
```

### 6. Invoke & Query

In another terminal:

```bash
cd /path/to/test-network-nano-bash
. ./peer1admin.sh

# Create an asset
ASSET_ID=my-asset-$(date +%s)
peer chaincode invoke \
  -o 127.0.0.1:6050 \
  -C mychannel \
  -n basic \
  -c '{"Args":["CreateAsset","'$ASSET_ID'","blue","10","alice","100"]}' \
  --waitForEvent \
  --tls \
  --cafile "$PWD/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt"

# Read the asset
peer chaincode query \
  -C mychannel \
  -n basic \
  -c '{"Args":["ReadAsset","'$ASSET_ID'"]}' \
  --tls \
  --cafile "$PWD/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt"
```

## Docker Deployment (Optional)

To run the chaincode in a Docker container:

```bash
cd /path/to/fabric-chaincode-python/examples/ccaas-basic

# Build the image
docker build -t fabric-python-ccaas .

# Run the container (ensure peer can reach it)
docker run --rm \
  --name fabric-python-ccaas \
  -e CHAINCODE_ID="basic_1.0:1009cf0fb390fe375c77a5771299732ceb10a87d2f36cb30c9d1eaf95427b55f" \
  -e CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999 \
  -p 9999:9999 \
  fabric-python-ccaas
```

**Note:** If the peer runs in a container, adjust the address and networking accordingly so the peer can reach the chaincode server.

## File Structure

```
examples/ccaas-basic/
├── main.py                # Chaincode implementation
├── connection.json        # Peer connection configuration
├── metadata.json          # CCAAS metadata (type: "ccaas")
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
└── README.md              # This file
```

## Key Configuration Files

### connection.json
Specifies where the chaincode server listens:
- `address`: Host and port for the server
- `dial_timeout`: Connection timeout
- `tls_required`: Whether TLS is required (false in this example)

### metadata.json
Tells Fabric that this is a CCAAS package:
- `type`: Must be `"ccaas"`
- `label`: Package label used for identification

## Troubleshooting

### Server won't start
- Ensure `CHAINCODE_ID` matches the package-id from `peer lifecycle chaincode install`
- Check that `connection.json` address is accessible from the peer
- Verify gRPC is installed: `pip install "grpcio>=1.83.1"`

### Peer can't reach chaincode
- Check firewall rules allowing port 9999
- Verify the address in `connection.json` is reachable from the peer's network
- Use `localhost` or `127.0.0.1` if peer runs on the same host

### Registration errors
- Look for "Successfully registered with peer node" in server logs
- Check peer logs for connection errors
- Ensure the `CHAINCODE_ID` environment variable is set correctly

## References

- [Hyperledger Fabric Chaincode as a Service](https://hyperledger-fabric.readthedocs.io/en/latest/cc_service.html)
- [Fabric Python Chaincode Repository](../)
- [Test Network Setup](../../../README.md)
