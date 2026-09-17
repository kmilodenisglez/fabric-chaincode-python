# Asset Transfer SBE — fabric-contract-api (CCAAS)

This is the high-level, contract-API counterpart of
[`examples/ccaas/fabric-shim/asset-transfer-sbe/`](../../fabric-shim/asset-transfer-sbe/).
It mirrors the function set of `fabric-samples/asset-transfer-sbe`:

- `InitLedger()`
- `CreateAsset(assetId, value, owner)`
- `ReadAsset(assetId)`
- `UpdateAsset(assetId, newValue)`
- `DeleteAsset(assetId)`
- `TransferAsset(assetId, newOwner, newOwnerOrg)`
- `AssetExists(assetId)`

On-chain JSON uses lowercase field names (`id`, `value`, `owner`,
`owner_org`) matching the `Asset` dataclass — this is what the contract
API's auto-generated schema also advertises, so clients querying the
metadata see consistent field names.  The fabric-shim SBE counterpart
uses Go-style CamelCase field names (`ID`/`Value`/`Owner`/`OwnerOrg`);
the two deployments are independent and do not share ledger state.

> **NOTE — State-Based Endorsement (SBE):** The Go `asset-transfer-sbe`
> sample applies key-level endorsement policies via
> `shim.SetStateValidationParameter`.  The Python shim in this repository
> does **not** yet expose `set_state_validation_parameter`, so this sample
> mirrors SBE field names and the transfer flow but cannot apply key-level
> endorsement policy from code.  When the shim gains that method this
> example can be extended to call it inside `CreateAsset` and
> `TransferAsset`.

## Why use the contract API?

Compared to the fabric-shim version of this sample, here you get:

- **Auto-dispatch** — no `if fn == "CreateAsset"` ladder; the framework
  reads the function name from the first arg and calls the right method.
- **Type-annotated parameters** — `value: int` is converted from the string
  arg by the JSON serializer; you don't need to write `int(value)` yourself.
- **Auto-generated metadata** — exposed via `org.hyperledger.fabric:get_metadata`.
- **Read-only tagging** — `ReadAsset` and `AssetExists` are tagged as
  `EVALUATE` in the metadata via `get_evaluate_transactions()`.

## Prerequisites

- Hyperledger Fabric test network running (e.g. `test-network-nano-bash`)
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
```

### 2. Package, Install, Approve, Commit

See the [fabric-shim SBE README](../../fabric-shim/asset-transfer-sbe/README.md)
for the full packaging / lifecycle sequence — the only difference is the
package label (`asset_transfer_sbe_contract_api_1` here) and the path to
`connection.json` / `metadata.json`:

```bash
cp examples/ccaas/fabric-contract-api/asset-transfer-sbe/connection.json chaincode-external/package/
cp examples/ccaas/fabric-contract-api/asset-transfer-sbe/metadata.json chaincode-external/
```

### 3. Start the Chaincode Server

```bash
cd /path/to/fabric-chaincode-python
source .venv/bin/activate
export CHAINCODE_ID="asset_transfer_sbe_contract_api_1:<package_hash>"
export CHAINCODE_SERVER_ADDRESS=127.0.0.1:9999
./.venv/bin/python examples/ccaas/fabric-contract-api/asset-transfer-sbe/main.py
```

### 4. Invoke & Query

```bash
cd /path/to/test-network-nano-bash
. ./peer1admin.sh

# Initialise with two sample assets
peer chaincode invoke -C mychannel -n asset-transfer-sbe \
  -c '{"Args":["InitLedger"]}'

# Create a new asset
peer chaincode invoke -C mychannel -n asset-transfer-sbe \
  -c '{"Args":["CreateAsset","asset3","150","carol"]}'

# Read it back
peer chaincode query -C mychannel -n asset-transfer-sbe \
  -c '{"Args":["ReadAsset","asset3"]}'

# Transfer to a new owner / org
peer chaincode invoke -C mychannel -n asset-transfer-sbe \
  -c '{"Args":["TransferAsset","asset3","dave","Org2MSP"]}'

# Check existence
peer chaincode query -C mychannel -n asset-transfer-sbe \
  -c '{"Args":["AssetExists","asset3"]}'
```

## Docker Deployment

```bash
cd /path/to/fabric-chaincode-python
docker build -f examples/ccaas/fabric-contract-api/asset-transfer-sbe/Dockerfile \
  -t asset-transfer-sbe-contract-api:latest .

docker run -d \
  --name asset-transfer-sbe-contract-api \
  -e CHAINCODE_ID=asset_transfer_sbe_contract_api_1:<package_hash> \
  -e CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999 \
  -p 9999:9999 \
  asset-transfer-sbe-contract-api:latest
```

## File Structure

```
examples/ccaas/fabric-contract-api/asset-transfer-sbe/
├── main.py                # Contract implementation + CCAAS entry point
├── connection.json        # Peer connection configuration
├── metadata.json          # CCAAS metadata (type: "ccaas")
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container image definition
└── README.md              # This file
```

## References

- [fabric-shim version of this sample](../../fabric-shim/asset-transfer-sbe/)
- [fabric_contract_api documentation](../../../src/fabric_contract_api/README.md)
- [Hyperledger Fabric SBE docs](https://hyperledger-fabric.readthedocs.io/en/latest/chaincode4no.html#state-based-endorsement)
