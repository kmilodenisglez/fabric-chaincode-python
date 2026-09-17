# Examples Directory Structure

This document describes the layout of the `examples/` directory, the
conventions every example follows, and how to add new ones.

## Layout

```
examples/
├── README.md                       # Top-level overview + scenario picker
├── STRUCTURE.md                    # This file
└── ccaas/                          # All examples are CCAAS
    ├── README.md                   # CCAAS-specific notes
    ├── fabric-shim/                # Low-level fabric_shim examples
    │   ├── README.md
    │   ├── asset-transfer-basic/
    │   │   ├── main.py             # Chaincode implementation + entry point
    │   │   ├── README.md           # Packaging + deployment walkthrough
    │   │   ├── connection.json     # Where the peer finds the chaincode
    │   │   ├── metadata.json       # Package label + type ("ccaas")
    │   │   ├── requirements.txt    # Python deps for this example
    │   │   └── Dockerfile          # Optional container image
    │   └── asset-transfer-sbe/
    │       ├── main.py
    │       ├── README.md
    │       ├── connection.json
    │       ├── metadata.json
    │       ├── requirements.txt
    │       └── Dockerfile
    └── fabric-contract-api/         # High-level fabric_contract_api examples
        ├── README.md
        ├── asset-transfer-basic/
        │   ├── main.py
        │   ├── README.md
        │   ├── connection.json
        │   ├── metadata.json
        │   ├── requirements.txt
        │   └── Dockerfile
        └── asset-transfer-sbe/
            ├── main.py
            ├── README.md
            ├── connection.json
            ├── metadata.json
            ├── requirements.txt
            └── Dockerfile
```

## Two layers, two scenarios

|              | fabric-shim                              | fabric-contract-api                                  |
| ------------ | ---------------------------------------- | ---------------------------------------------------- |
| Package      | `src.fabric_shim`                        | `src.fabric_contract_api`                            |
| Base class   | `Chaincode`                              | `Contract`                                           |
| Dispatch     | Manual `if action == "..."` in `invoke`  | Automatic via reflection on contract methods        |
| Arguments    | `list[str]` — parse yourself             | Type-annotated Python parameters (dataclasses OK)   |
| Returns      | `pb.Response(status=..., payload=...)`   | Plain Python value — serializer converts to bytes    |
| Metadata     | Not generated                            | Auto-generated, exposed via `org.hyperledger.fabric:get_metadata` |
| Read-only tag| Not supported                            | `get_evaluate_transactions()` returns the list      |
| Code style   | Imperative                               | Declarative                                          |

Each scenario exists in **both** layers so you can compare:

- `asset-transfer-basic`: InitLedger / CreateAsset / ReadAsset /
  UpdateAsset / DeleteAsset / GetAllAssets.
- `asset-transfer-sbe`: the above minus `GetAllAssets`, plus
  `TransferAsset` and `AssetExists`.  On-chain JSON uses the Go SBE field
  names (`ID` / `Value` / `Owner` / `OwnerOrg`).

## Conventions

Every example follows these conventions so they're easy to compare and
swap:

### `main.py`

- Single self-contained file.
- Resolves the repository root at runtime by walking up the parent
  chain looking for `src/fabric_shim` (or `src/fabric_contract_api`).
  This makes the example runnable from any working directory.
- Exposes a `build_chaincode()` factory (used by tests) and a `main()`
  entry point.
- Uses `from __future__ import annotations` so type hints work with
  PEP 563 string-form annotations.

### `connection.json`

```json
{
  "address": "127.0.0.1:9999",
  "dial_timeout": "10s",
  "tls_required": false
}
```

### `metadata.json`

```json
{
  "path": "",
  "type": "ccaas",
  "label": "<example_label>_1"
}
```

The `label` is unique per example so multiple chaincodes can coexist on
the same peer.

### `requirements.txt`

Each example pins the subset of dependencies it actually uses.  When
in doubt, install the parent repo's `requirements.txt` from the
repository root — it includes everything every example needs.

### `Dockerfile`

Built from the **repository root** as Docker context, so the entire
`src/` tree is copied into the image.  Example:

```bash
docker build -f examples/ccaas/<layer>/<scenario>/Dockerfile \
  -t <scenario>-<layer>:latest .
```

### `README.md`

Each README follows this template:

1. **One-paragraph overview** — what the example does and how it
   differs from its sibling in the other layer.
2. **Prerequisites** — Fabric network, Python version, peer CLI.
3. **Quick Start** — numbered steps: prepare venv, package, install,
   approve, commit, start server, invoke, query.
4. **Docker Deployment** — `docker build` + `docker run` commands.
5. **File Structure** — what each file in the example directory is for.
6. **References** — links to the sibling example in the other layer,
   the package documentation, and the official Fabric docs.

## Adding a new example

1. Pick the **layer** (`ccaas/fabric-shim/` or
   `ccaas/fabric-contract-api/`).
2. Pick a **scenario name** (e.g. `asset-transfer-secured-auction`).
3. Create the directory: `ccaas/<layer>/<scenario>/`.
4. Copy the file set from the closest existing example.
5. Implement the chaincode in `main.py`.
6. Adjust `metadata.json`'s `label` so it's unique.
7. Write the `README.md` following the template above.
8. Add a row to the table in `ccaas/<layer>/README.md`.
9. Add a row to the table in `examples/README.md`.
10. (Optional) Add a row to the table at the top of this file.

## Integration with the parent project

Each example:

- References the parent `src/fabric_shim/` and / or
  `src/fabric_contract_api/` for the framework.
- Uses the parent `requirements.txt` or specifies its own subset.
- Operates independently once deployed — the chaincode process does not
  need the source tree at runtime as long as `PYTHONPATH=/app` is set
  inside the Docker image (or the venv has the package installed).

## Guidelines

✅ **DO:**
- Include clear, step-by-step README instructions.
- Use realistic asset management logic.
- Provide Docker support.
- Add error handling and validation.
- Test thoroughly before committing.
- Document all assumptions and prerequisites.

❌ **DON'T:**
- Skip documentation.
- Use hardcoded credentials or secrets.
- Create incomplete or non-working examples.
- Assume the user knows all Fabric concepts.
- Forget to update the layer README and `examples/README.md`.
