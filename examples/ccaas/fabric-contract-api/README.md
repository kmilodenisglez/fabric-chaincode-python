# fabric-contract-api Examples (CCAAS)

These examples use the high-level **`fabric_contract_api`** package,
which is the Python equivalent of Go's
[`fabric-contract-api-go`](https://github.com/hyperledger/fabric-contract-api-go).
You subclass [`Contract`](../../../src/fabric_contract_api/contractapi/contract.py)
and declare each transaction as a public async method — the framework
handles dispatch, argument conversion, metadata generation, and
schema validation automatically.

## When to choose fabric-contract-api

- You want to focus on **business logic** rather than request dispatch.
- You want **typed parameters** — `def CreateAsset(self, ctx, asset: Asset)`
  instead of `inputs[0]`, `inputs[1]`, ...
- You want **auto-generated metadata** exposed through the built-in
  `org.hyperledger.fabric:get_metadata` system contract.
- You want **read-only transaction tagging** (`EVALUATE` vs `SUBMIT`) via
  `get_evaluate_transactions()`.
- You're porting a Go chaincode that uses `contractapi.Contract` and want
  the structure to match 1:1.

## Examples

| Example                                                            | Description                                                                         |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| [`asset-transfer-basic`](./asset-transfer-basic/)                  | Asset CRUD with an `Asset` dataclass — same scenario as the fabric-shim version     |
| [`asset-transfer-sbe`](./asset-transfer-sbe/)                     | Asset transfer mirroring `fabric-samples/asset-transfer-sbe` (with TransferAsset)  |

Each example's transactions match its fabric-shim counterpart
function-for-function so you can compare them side-by-side and see what
the contract API buys you.

## Compare with fabric-shim

For the **same** scenarios built on the low-level `fabric_shim` package
(manual dispatch, manual `json.loads`, no metadata), see
[`../fabric-shim/`](../fabric-shim/).

## Running any example

Each example has its own `README.md` with full packaging + deployment
instructions.  The common pattern is identical to the fabric-shim
examples:

1. `pip install -r requirements.txt` (from the repository root).
2. Build the CCAAS package using the example's `connection.json` /
   `metadata.json`.
3. `peer lifecycle chaincode install / approveformyorg / commit`.
4. Start the chaincode process:
   ```bash
   export CHAINCODE_ID="<package_id>"
   export CHAINCODE_SERVER_ADDRESS="127.0.0.1:9999"
   python examples/ccaas/fabric-contract-api/<example-name>/main.py
   ```
5. `peer chaincode invoke` / `query` against the running chaincode —
   including the metadata query:
   ```bash
   peer chaincode query -C mychannel -n <name> \
     -c '{"Args":["org.hyperledger.fabric:get_metadata"]}'
   ```
