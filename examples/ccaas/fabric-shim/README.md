# fabric-shim Examples (CCAAS)

These examples use the low-level **`fabric_shim`** package directly. You
subclass [`Chaincode`](../../../src/fabric_shim/interfaces.py) and write
`init` / `invoke` methods, dispatching on the function name by hand.

## When to choose fabric-shim

- You need **fine-grained control** over the response (custom status codes,
  custom payloads).
- You want **zero reflection** — the dispatch table is explicit in your
  code.
- You're porting a Go chaincode that uses `shim.Chaincode` directly and
  want to keep the structure 1:1.
- You don't need auto-generated metadata.

## Examples

| Example                                                            | Description                                                                         |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| [`asset-transfer-basic`](./asset-transfer-basic/)                  | Asset CRUD (Create / Read / Update / Delete / InitLedger / GetAllAssets)           |
| [`asset-transfer-sbe`](./asset-transfer-sbe/)                     | Asset transfer mirroring `fabric-samples/asset-transfer-sbe` (with TransferAsset)  |

## Compare with fabric-contract-api

For the **same** scenarios built on the high-level `fabric_contract_api`
package (which handles dispatch, type-conversion, and metadata generation
automatically), see
[`../fabric-contract-api/`](../fabric-contract-api/).

## Running any example

Each example has its own `README.md` with full packaging + deployment
instructions.  The common pattern is:

1. `pip install -r requirements.txt` (from the repository root).
2. Build the CCAAS package using the example's `connection.json` /
   `metadata.json`.
3. `peer lifecycle chaincode install / approveformyorg / commit`.
4. Start the chaincode process:
   ```bash
   export CHAINCODE_ID="<package_id>"
   export CHAINCODE_SERVER_ADDRESS="127.0.0.1:9999"
   python examples/ccaas/fabric-shim/<example-name>/main.py
   ```
5. `peer chaincode invoke` / `query` against the running chaincode.
