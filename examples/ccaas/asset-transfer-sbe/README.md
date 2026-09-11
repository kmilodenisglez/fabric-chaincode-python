# Token Chaincode - CCAAS Example

This directory contains a complete example of a Hyperledger Fabric Python chaincode for token management deployed as a Chaincode-as-a-Service (CCAAS).

## Overview

This example implements a simple token system where you can:
- **reset** - Reset token balances for all accounts (equivalent to init)
- **balance** - Query the token balance of an account
- **transfer** - Transfer tokens from one account to another

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
cd examples/token_chaincode
pip install -r requirements.txt
```

### 3. Run the Chaincode Server

```bash
export CHAINCODE_ID=token_1.0:sha256:your_package_hash
export CHAINCODE_SERVER_ADDRESS=127.0.0.1:9999

cd examples/token_chaincode
python main.py
```

The chaincode server will start and wait for connections from a Fabric peer.

### 4. Invoke Chaincode Functions

**Initialize/Reset tokens:**
```bash
peer chaincode invoke -C mychannel -n token_1.0 -c '{"function":"reset","Args":[]}'
```

**Query balance:**
```bash
peer chaincode query -C mychannel -n token_1.0 -c '{"function":"balance","Args":["tommy"]}'
```

**Transfer tokens:**
```bash
peer chaincode invoke -C mychannel -n token_1.0 -c '{"function":"transfer","Args":["tommy","jerry","100"]}'
```

**Check new balances:**
```bash
peer chaincode query -C mychannel -n token_1.0 -c '{"function":"balance","Args":["tommy"]}'
peer chaincode query -C mychannel -n token_1.0 -c '{"function":"balance","Args":["jerry"]}'
```

## Docker Deployment

### Build the Docker Image

```bash
docker build -t token-chaincode:latest .
```

### Run in Docker

```bash
docker run -d \
  --name token-chaincode \
  -e CHAINCODE_ID=token_1.0:sha256:your_hash \
  -e CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999 \
  -p 9999:9999 \
  token-chaincode:latest
```

### Use in Fabric Network

Package and deploy the chaincode to your Fabric network following the [official Hyperledger Fabric documentation](https://hyperledger-fabric.readthedocs.io/en/latest/chaincode4ade.html).

## Project Structure

```
token_chaincode/
├── main.py               # Chaincode implementation
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container image definition
├── README.md           # This file
└── metadata.json       # Chaincode metadata (optional)
```

## API Reference

### Functions

#### `reset`
Initializes/resets token balances for test accounts.

**Parameters:** None

**Returns:** `success: b'init ok'` or error message

#### `balance`
Queries the token balance of an account.

**Parameters:**
- `account` (string): Account name

**Returns:** `success: b'balance => <amount>'` or error message

#### `transfer`
Transfers tokens from one account to another.

**Parameters:**
- `from` (string): Source account name
- `to` (string): Destination account name
- `amount` (string): Amount to transfer (must be convertible to integer)

**Returns:** `success: b'transfer ok'` or error message

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

- [Asset Transfer (CCAAS)](../ccaas/) - More complex asset management example
- [Fabric Chaincode Python Documentation](../../README.md)

## License

This example is licensed under the Apache-2.0 License. See [LICENSE](../../LICENSE) for details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
