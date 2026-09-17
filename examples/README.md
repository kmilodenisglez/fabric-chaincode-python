# Examples

This directory contains example implementations of Hyperledger Fabric
Python chaincodes.  **All examples are CCAAS** (Chaincode-as-a-Service) —
the chaincode runs as a long-lived gRPC server that the Fabric peer
connects to.

## Layout

```
examples/
├── README.md                       # This file
├── STRUCTURE.md                    # Explanation of the layout & conventions
└── ccaas/                          # All CCAAS examples
    ├── README.md                   # CCAAS overview
    ├── fabric-shim/                # Low-level fabric_shim API examples
    │   ├── README.md
    │   ├── asset-transfer-basic/  # Asset CRUD (manual dispatch)
    │   └── asset-transfer-sbe/     # SBE-style transfer (manual dispatch)
    └── fabric-contract-api/        # High-level fabric_contract_api examples
        ├── README.md
        ├── asset-transfer-basic/   # Asset CRUD (auto-dispatch + metadata)
        └── asset-transfer-sbe/     # SBE-style transfer (auto-dispatch + metadata)
```

## Pick your API layer

| Layer                    | Use when you want …                                              | Package                  |
| ------------------------ | ---------------------------------------------------------------- | ------------------------ |
| `ccaas/fabric-shim/`     | Fine-grained control, manual dispatch, zero reflection          | `src.fabric_shim`        |
| `ccaas/fabric-contract-api/` | Auto-dispatch, type-annotated args, auto-generated metadata | `src.fabric_contract_api` |

Both layers expose the **same scenarios** (asset-transfer-basic and
asset-transfer-sbe) so you can compare implementations side-by-side.

## Pick a scenario

| Scenario                  | What it shows                                                 |
| ------------------------- | ------------------------------------------------------------- |
| `asset-transfer-basic/`   | Asset CRUD: InitLedger, CreateAsset, ReadAsset, UpdateAsset, DeleteAsset, GetAllAssets |
| `asset-transfer-sbe/`     | SBE-style: the above plus `TransferAsset` and `AssetExists`  |

## Quick start

1. **Choose**: pick one of `ccaas/fabric-shim/<scenario>/` or
   `ccaas/fabric-contract-api/<scenario>/`.
2. **Read**: each example has its own `README.md` with the full
   packaging / install / approve / commit / run / invoke / query
   sequence.
3. **Run**: from the repository root,
   ```bash
   pip install -r requirements.txt
   export CHAINCODE_ID="<package_id>"
   export CHAINCODE_SERVER_ADDRESS="127.0.0.1:9999"
   python examples/ccaas/<layer>/<scenario>/main.py
   ```

## What is CCAAS?

**Chaincode-as-a-Service (CCAAS)** is a deployment model for Hyperledger
Fabric chaincodes where:

- The chaincode runs as an independent service/process.
- The peer connects to it via gRPC.
- You have full control over the runtime environment.
- Perfect for integrating with external systems, databases, or
  microservices.

See the [official Fabric docs](https://hyperledger-fabric.readthedocs.io/en/latest/cc_service.html)
for more details on the CCAAS architecture.

## Requirements

- Python 3.10+
- Hyperledger Fabric network (test network or production)
- Peer CLI for lifecycle management
- Docker (optional, for containerized deployment)

## Related Documentation

- [`fabric_shim` package](../src/fabric_shim/) — low-level chaincode shim.
- [`fabric_contract_api` package](../src/fabric_contract_api/) — high-level
  contract API (Python port of `fabric-contract-api-go`).
- [Hyperledger Fabric Official Docs](https://hyperledger-fabric.readthedocs.io/)
- [CCAAS Architecture](https://hyperledger-fabric.readthedocs.io/en/latest/cc_service.html)

## Contributing

If you create a new example, follow the same structure:

1. Create a new folder under `ccaas/<layer>/<scenario>/`.
2. Include at least `main.py`, `README.md`, `connection.json`,
   `metadata.json`, `requirements.txt`, `Dockerfile`.
3. Update `ccaas/<layer>/README.md` to reference the new example.
4. Add a row to the tables in this README and in `STRUCTURE.md`.
