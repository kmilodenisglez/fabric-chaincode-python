# Asset Transfer Basic — fabric-contract-api (CCAAS)

This is the high-level, contract-API counterpart of
[`examples/ccaas/fabric-shim/asset-transfer-basic/`](../../fabric-shim/asset-transfer-basic/).
It implements the **same** asset-management transactions
(`InitLedger`, `CreateAsset`, `ReadAsset`, `UpdateAsset`, `DeleteAsset`,
`GetAllAssets`) but uses the `fabric_contract_api` package, which:

- **Auto-dispatches** Init/Invoke calls to the right contract method — you
  don't write a big `if action == "..."` dispatcher.
- **Auto-converts** the string args coming from the peer into typed Python
  values (via the JSON serializer) — e.g. `CreateAsset(ctx, asset_id: str,
  color: str, size: int, owner: str, appraised_value: int)` receives
  properly-typed scalars; you don't have to write `int(inputs[2])`
  yourself.
- **Auto-generates** JSON-Schema metadata and exposes it through the
  built-in `org.hyperledger.fabric:get_metadata` system contract.
- **Validates** parameter and return types against the JSON schema at
  runtime (when `jsonschema` is installed).

## Comparison with the fabric-shim version

| Concern                          | fabric-shim version               | fabric-contract-api version                     |
| -------------------------------- | --------------------------------- | ----------------------------------------------- |
| Dispatch                          | Hand-rolled `if action == ...`    | Automatic, via reflection                       |
| Argument types                    | `inputs[0]`, `inputs[1]`, ...      | Named, type-annotated Python parameters         |
| Numeric conversion                | Manual `int(inputs[2])`            | Automatic via the JSON serializer               |
| Metadata / `GetMetadata`          | Not provided                      | Auto-generated, exposed via system contract     |
| Read-only tagging (`EVALUATE`)   | Not provided                      | `get_evaluate_transactions()` returns the list  |
| Code size                         | ~135 lines                        | ~150 lines (most are docstrings)               |

> **Note on signatures**: in the Go `asset-transfer-basic` sample (and
> in the fabric-shim version of this sample), `CreateAsset` / `UpdateAsset`
> take 5 separate scalar args — `id`, `color`, `size`, `owner`,
> `appraised_value`.  This contract-API version uses the same signature
> so the same `peer chaincode invoke -c '{"Args":["CreateAsset","1","blue","35","jerry","1000"]}'`
> command works for both versions.  The internal `Asset` dataclass is
> built by the contract function from those scalars — clients never
> have to send a JSON-encoded object.

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

### 2. Package the Chaincode

From the repository root:

```bash
mkdir -p chaincode-external/package

cp examples/ccaas/fabric-contract-api/asset-transfer-basic/connection.json chaincode-external/package/
cp examples/ccaas/fabric-contract-api/asset-transfer-basic/metadata.json chaincode-external/

cd chaincode-external
tar -C package -czf code.tar.gz connection.json
tar -czf external-chaincode.tgz code.tar.gz metadata.json
cd ..
```

### 3. Install, Approve, Commit

See the [fabric-shim version's README](../../fabric-shim/asset-transfer-basic/README.md#3-install-on-peer)
for the full `peer lifecycle` sequence — the commands are identical, only
the package label differs (`basic_contract_api_1` here).

### 4. Start the Chaincode Server

```bash
cd /path/to/fabric-chaincode-python
source .venv/bin/activate

# Get the installed package ID
cd /path/to/test-network-nano-bash
. ./peer1admin.sh
PACKAGE_ID=$(peer lifecycle chaincode queryinstalled --output json | \
  jq -r '.installed_chaincodes[] | select(.label == "basic_contract_api_1") | .package_id')

# Start the server
cd /path/to/fabric-chaincode-python
export CHAINCODE_ID="$PACKAGE_ID"
export CHAINCODE_SERVER_ADDRESS=127.0.0.1:9999
./.venv/bin/python examples/ccaas/fabric-contract-api/asset-transfer-basic/main.py
```

### 5. Invoke & Query

```bash
cd /path/to/test-network-nano-bash
. ./peer1admin.sh

# Create an asset — 5 separate scalar args (matches the Go sample
# and the fabric-shim version of this chaincode).
ASSET_ID=my-asset-$(date +%s)
peer chaincode invoke \
  -o 127.0.0.1:6050 \
  -C mychannel \
  -n basic \
  -c '{"Args":["CreateAsset","'"$ASSET_ID"'","blue","10","alice","100"]}' \
  --waitForEvent \
  --tls \
  --cafile "$PWD/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt"

# Update the asset — same 5 scalar args.
peer chaincode invoke \
  -o 127.0.0.1:6050 \
  -C mychannel \
  -n basic \
  -c '{"Args":["UpdateAsset","'"$ASSET_ID"'","green","20","alice","200"]}' \
  --waitForEvent \
  --tls \
  --cafile "$PWD/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt"

# Read the asset — peer chaincode query prints the JSON to stdout.
peer chaincode query \
  -C mychannel \
  -n basic \
  -c '{"Args":["ReadAsset","'"$ASSET_ID"'"]}'

# Inspect auto-generated chaincode metadata
peer chaincode query \
  -C mychannel \
  -n basic \
  -c '{"Args":["org.hyperledger.fabric:get_metadata"]}'
```

## Docker Deployment (Optional)

```bash
cd /path/to/fabric-chaincode-python
docker build -f examples/ccaas/fabric-contract-api/asset-transfer-basic/Dockerfile \
  -t fabric-python-contract-api .

docker run --rm \
  --name fabric-python-contract-api \
  -e CHAINCODE_ID="basic_contract_api_1:<hash>" \
  -e CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999 \
  -p 9999:9999 \
  fabric-python-contract-api
```

## File Structure

```
examples/ccaas/fabric-contract-api/asset-transfer-basic/
├── main.py                # Contract implementation + CCAAS entry point
├── connection.json        # Peer connection configuration
├── metadata.json          # CCAAS metadata (type: "ccaas")
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
└── README.md              # This file
```

## References

- [fabric-shim version of this sample](../../fabric-shim/asset-transfer-basic/)
- [fabric_contract_api documentation](../../../src/fabric_contract_api/README.md)
- [Hyperledger Fabric Chaincode as a Service](https://hyperledger-fabric.readthedocs.io/en/latest/cc_service.html)
