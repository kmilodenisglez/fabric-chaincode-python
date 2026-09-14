Protobufs / How this project uses `fabric-protos`
===============================================

Current integration model
-------------------------

This project now consumes official Python protobuf bindings from
`hyperledger/fabric-protos`.

- Package name: `hyperledger-fabric-protos`
- Import namespace used by this repository: `fabric_protos`

Install with:

```bash
PYTHON_BIN=python ./scripts/install_fabric_protos.sh
```

Why this model
--------------

- Avoids vendored generated protobuf drift inside this repository.
- Keeps protocol bindings aligned with the upstream Fabric protobuf source.
- Simplifies release and maintenance for `fabric-chaincode-python`.

Version compatibility
---------------------

Use dependency ranges compatible with upstream Python bindings:

- `protobuf>=5.27.0,<6.0.0`
- `grpcio>=1.83.1,<2.0.0`

The installer script uses the following order:

1. Local `../fabric-protos` checkout (runs `make pythonbindings`)
2. PyPI `hyperledger-fabric-protos` package (if complete)
3. Official `hyperledger/fabric-protos` git checkout at pinned commit,
   then local build/install of `bindings/python`

Local regeneration (optional)
-----------------------------

For debugging or contributor workflows, bindings can still be generated from
a local `fabric-protos` checkout:

```bash
PROTO_SRC=/path/to/fabric-protos OUT_DIR=$PWD/fabric_protos bash scripts/gen_protos.sh
```

This is optional and should not be required for normal runtime use.

License
-------

`fabric-protos` is Apache-2.0. If distributing generated bindings yourself,
keep original licensing notices intact.
