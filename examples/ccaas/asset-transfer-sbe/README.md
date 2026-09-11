# Asset Transfer SBE - CCAAS Example

This directory contains a complete example of a Hyperledger Fabric Python chaincode aligned with the `asset-transfer-sbe` sample and deployed as Chaincode-as-a-Service (CCAAS).

## Overview

This example implements the `asset-transfer-sbe` function set:
- **CreateAsset**
- **ReadAsset**
- **UpdateAsset**
- **DeleteAsset**
- **TransferAsset**
- **AssetExists**

## Features

- ✅ Async/await chaincode implementation
- ✅ Error handling and validation
- ✅ Logging for debugging
- ✅ Input validation (amount must be numeric)
- ✅ Balance checks before transfers
- ✅ Account existence validation
- ✅ CCAAS deployment ready
- ✅ Docker support

## Prerequisites

- Hyperledger Fabric test network running (e.g., `test-network-nano-bash`)
- Python 3.10+ with `venv`
- Peer CLI (`peer`) configured and in PATH
- The parent `fabric-chaincode-python` repository available
- Docker (optional, for containerized deployment)

## Quick Start

### 1. Prepare Python Environment

```bash
cd /path/to/fabric-chaincode-python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Example Dependencies

```bash
cd examples/ccaas/asset-transfer-sbe
pip install -r requirements.txt
```

### 3. Run the Chaincode Server

```bash
export CHAINCODE_ID=asset_transfer_sbe_1:<package_hash>
export CHAINCODE_SERVER_ADDRESS=127.0.0.1:9999

python main.py
```

The chaincode server will start and wait for connections from a Fabric peer.

### 4. Invoke Chaincode Functions

**Create asset:**
```bash
peer chaincode invoke -C mychannel -n asset-transfer-sbe -c '{"Args":["CreateAsset","asset1","100","alice"]}'
```

**Read asset:**
```bash
peer chaincode query -C mychannel -n asset-transfer-sbe -c '{"Args":["ReadAsset","asset1"]}'
```

**Transfer asset:**
```bash
peer chaincode invoke -C mychannel -n asset-transfer-sbe -c '{"Args":["TransferAsset","asset1","bob","Org2MSP"]}'
```

## Docker Deployment

### Build the Docker Image

```bash
docker build -f examples/ccaas/asset-transfer-sbe/Dockerfile -t asset-transfer-sbe:latest .
```

### Run in Docker

```bash
docker run -d \
  --name asset-transfer-sbe \
  -e CHAINCODE_ID=asset_transfer_sbe_1:<package_hash> \
  -e CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999 \
  -p 9999:9999 \
  asset-transfer-sbe:latest
```

### Use in Fabric Network

Package and deploy the chaincode to your Fabric network following the [official Hyperledger Fabric documentation](https://hyperledger-fabric.readthedocs.io/en/latest/chaincode4ade.html).

## Project Structure

```
asset-transfer-sbe/
├── main.py               # Chaincode implementation
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container image definition
├── README.md           # This file
└── metadata.json       # Chaincode metadata (optional)
```

## API Reference

### Functions

#### `CreateAsset(assetId, value, owner)`
Creates a new asset and records owner/org metadata.

#### `ReadAsset(assetId)`
Returns the stored JSON for one asset.

#### `TransferAsset(assetId, newOwner, newOwnerOrg)`
Transfers ownership fields to a new owner/org.

## Error Handling

The chaincode includes comprehensive error handling:
- Account not found errors
- Insufficient balance errors
- Invalid amount errors (non-numeric input)
- Missing argument errors

All errors are logged and returned with descriptive messages.

## Testing

Run the included tests:

```bash
cd /path/to/fabric-chaincode-python
pytest tests/
```

## Logging

The chaincode uses Python's standard logging module with DEBUG level logging.

To adjust logging level, modify the `logging.basicConfig()` call in `main.py`:

```python
logging.basicConfig(level=logging.INFO)  # Change to INFO, WARNING, etc.
```

## Related Examples

- [Asset Transfer Basic (CCAAS)](../asset-transfer-basic/) - Baseline asset transfer example
- [Fabric Chaincode Python Documentation](../../README.md)

## License

This example is licensed under the Apache-2.0 License. See [LICENSE](../../LICENSE) for details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
