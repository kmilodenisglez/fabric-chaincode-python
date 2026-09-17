# CCAAS Examples

All examples in this directory are deployed as
**Chaincode-as-a-Service (CCAAS)** — the chaincode runs as an
independent gRPC server process, and the Fabric peer connects to it
rather than launching a container per chaincode instance.

CCAAS is the recommended deployment model when you want to:

- Run the chaincode in a long-lived process with warm caches.
- Integrate with external systems (databases, message queues, etc.).
- Use a language runtime that is hard to package as a Docker image
  (e.g. a specific Python version with system-level dependencies).
- Update the chaincode binary without going through the full
  `peer lifecycle` flow.

## Layout

```
ccaas/
├── README.md                  # This file
├── fabric-shim/               # Low-level API (manual dispatch)
│   ├── README.md
│   ├── asset-transfer-basic/ # Asset CRUD
│   └── asset-transfer-sbe/   # Asset transfer (SBE-style fields)
└── fabric-contract-api/      # High-level API (auto-dispatch + metadata)
    ├── README.md
    ├── asset-transfer-basic/ # Asset CRUD with dataclass + auto-metadata
    └── asset-transfer-sbe/   # SBE function set with auto-metadata
```

The two layers expose the **same scenarios** so you can pick the API
style you prefer:

- **`fabric-shim/`** — you subclass `Chaincode` and write
  `init` / `invoke` methods.  Dispatch is a hand-rolled `if action == ...`
  ladder; arguments come in as a `list[str]` you parse yourself.
- **`fabric-contract-api/`** — you subclass `Contract` and declare each
  transaction as a public async method with type-annotated parameters.
  Dispatch, type conversion, and metadata generation happen
  automatically.

## Quick start

1. **Pick an API layer**: `fabric-shim/` or `fabric-contract-api/`.
2. **Pick a scenario**: `asset-transfer-basic/` (CRUD) or
   `asset-transfer-sbe/` (with transfer).
3. **Open the example's `README.md`** — it has the full packaging,
   install, approve, commit, run, invoke, and query sequence.

## Common prerequisites

- Hyperledger Fabric test network running (e.g. `test-network-nano-bash`)
- Python 3.10+
- Peer CLI (`peer`) configured and in PATH
- The parent `fabric-chaincode-python` repository available

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

## Environment variables

Every example reads these from the environment at startup:

| Variable                     | Required | Description                                                          |
| ---------------------------- | -------- | -------------------------------------------------------------------- |
| `CHAINCODE_SERVER_ADDRESS`   | yes      | Host:port for the gRPC server, e.g. `0.0.0.0:9999`                   |
| `CHAINCODE_ID`               | yes      | The package ID returned by `peer lifecycle chaincode install`        |
| `CORE_TLS_CLIENT_KEY_PATH`   | no       | Path to the TLS client key (when TLS is enabled)                    |
| `CORE_TLS_CLIENT_CERT_PATH`  | no       | Path to the TLS client cert                                          |
| `CORE_PEER_TLS_ROOTCERT_FILE`| no       | Path to the peer's TLS root CA cert                                  |
