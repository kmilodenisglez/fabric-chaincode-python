Protobufs / How this project uses `fabric-protos`
===============================================

Current integration model
-------------------------

This project consumes the official Python protobuf bindings published to PyPI from `hyperledger/fabric-protos`.

- Package name: `hyperledger-fabric-protos`
- Import namespace used by this repository: `fabric_protos`

The package is installed as a regular dependency:

```bash
pip install -r requirements.txt
```

For contributors: custom bindings

`scripts/install_fabric_protos.sh` remains available for contributors who need bindings not published to PyPI (an unreleased upstream commit, or a local checkout). Normal users do not need to run it; it is a no-op when a working fabric_protos is already importable.

Installation order of preference:

1. Do nothing if a working `fabric_protos` is already importable.
2. Local checkout from `FABRIC_PROTOS_SRC` (runs `make pythonbindings`).
3. Default sibling checkout ../fabric-protos, if present.
4. PyPI package `hyperledger-fabric-protos`.
5. Git checkout of `hyperledger/fabric-protos` at `FABRIC_PROTOS_REF`,then local build/install of bindings/python.

Test against a local fabric-protos checkout
-------------------------

```bash
FABRIC_PROTOS_SRC=/path/to/fabric-protos PYTHON_BIN=python ./scripts/install_fabric_protos.sh
```

Test against a specific upstream commit
-------------------------

```bash
FABRIC_PROTOS_REF=<commit-sha> PYTHON_BIN=python ./scripts/install_fabric_protos.sh
````

The script validates after install that the required generated modules 
- `fabric_protos.peer.chaincode_pb2`
- `fabric_protos.peer.chaincode_shim_pb2`
- `fabric_protos.common.common_pb2`

are importable.

Local regeneration (optional)
-----------------------------

For debugging or contributor workflows, bindings can still be generated from
a local `fabric-protos` checkout:

```bash
PROTO_SRC=/path/to/fabric-protos OUT_DIR=$PWD/fabric_protos bash scripts/gen_protos.sh
```

This is optional and should not be required for normal runtime use

License
-------

`fabric-protos` is Apache-2.0. If distributing generated bindings yourself,
keep original licensing notices intact.