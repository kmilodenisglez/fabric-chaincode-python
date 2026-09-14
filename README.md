# fabric-chaincode-python

Hyperledger Fabric Chaincode shim and Contract API for Python.

Status
------
- Experimental implementation of a Python chaincode shim and contract API.
- CI runs with Python 3.11; supported Python versions are 3.10 and 3.11.

Requirements
------------
- Python 3.10+ (3.11 recommended)
- See `requirements.txt` for runtime dependencies. Key packages:
	- `grpcio==1.83.1`
	- `protobuf>=5.27.0,<6.0.0`
	- `grpclib==0.4.3`
	- `hyperledger-fabric-protos` (installed via `scripts/install_fabric_protos.sh`)

Quick start (development)
-------------------------
Clone the repository and create a virtual environment:

```bash
git clone https://github.com/kmilodenisglez/fabric-chaincode-python.git
cd fabric-chaincode-python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
PYTHON_BIN=python ./scripts/install_fabric_protos.sh
```

Run tests:

```bash
pytest -q
```

Build a wheel (release)
-----------------------
Build a wheel that can be published or installed:

```bash
python -m pip install --upgrade build
python -m build --wheel --no-isolation
# artifact will be in dist/*.whl
```

Protobuf bindings
-----------------
This repository consumes the official Python bindings published from
`hyperledger/fabric-protos`:

- Package name: `hyperledger-fabric-protos`
- Import namespace: `fabric_protos`

Bindings are installed from official `hyperledger/fabric-protos` sources by
`scripts/install_fabric_protos.sh`, with validation that required generated
modules are present.

Install or refresh official bindings with:

```bash
PYTHON_BIN=python ./scripts/install_fabric_protos.sh
```

No vendored protobuf runtime package is required in this repository.
If you need to regenerate bindings locally for debugging, use
`scripts/gen_protos.sh` and keep generated/runtime versions compatible.

Running a chaincode service (example)
------------------------------------
Set the environment variables expected by the example chaincode server:

```bash
export CHAINCODE_ID=basic_1.0:your_package_id_here
export CHAINCODE_SERVER_ADDRESS=127.0.0.1:9999
```

Then start the example service (if `main.py` or an example is present):

```bash
./.venv/bin/python examples/ccaas/asset-transfer-basic/main.py
```

Contributing
------------
- Follow the Developer Certificate of Origin (DCO): sign commits with
	`Signed-off-by: Your Name <you@example.com>` (the repository contains a
	DCO check workflow).
- The project uses the Apache-2.0 license.

Releasing
---------
For information on how to create releases and publish to PyPI, see [RELEASING.md](RELEASING.md).

More information
----------------
- [RELEASING.md](RELEASING.md) — Release process and PyPI publishing
- [PROTOS.md](PROTOS.md) — Guidance on handling Fabric protobufs
- `scripts/gen_protos.sh` — Protobuf binding regeneration instructions
