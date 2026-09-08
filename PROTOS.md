Protobufs / How to handle `fabric-protos`
=========================================

Summary
-------

Hyperledger Fabric defines its gRPC interfaces in the `fabric-protos` repository
(Apache-2.0). When implementing a Python shim you generally have two practical
options:

1. "Submodule and generate": Add `fabric-protos` as a submodule (or reference a
	 fixed tag) and generate Python bindings (`*_pb2.py`, `*_pb2_grpc.py`) using
	 `grpc_tools.protoc` or `protoc` with a Python plugin. The provided
	 `scripts/gen_protos.sh` can be used for this. Optionally include the
	 generated files in the package for releases to simplify consumers' setup.

2. "Package pre-generated protos": Commit the generated Python bindings into
	 the repository/package and document the exact `fabric-protos` version used to
	 generate them. This avoids requiring consumers to generate bindings locally.

Recommendation (practical balance)
----------------------------------

- Use `fabric-protos` as a submodule pinned to the exact tag you support. This
	preserves provenance and makes regenerating bindings reproducible.
- Keep `scripts/gen_protos.sh` in the repo as a canonical way to regenerate
	bindings. Commit generated bindings for release artifacts (or for ease of
	testing), but avoid mixing `.proto` sources into the runtime package unless
	required.
- In CI, either regenerate the bindings and compare them with the committed
	files, or regenerate them as part of the release build to ensure consistency.
- Avoid publishing a PyPI package name that could be confused with an official
	upstream package (e.g. `fabric-protos-python`). If publishing generated
	bindings, choose a clear, distinct package name and document compatibility.

Practical steps (example)
-------------------------

1. Add `fabric-protos` as a submodule and pin to a tag:

```bash
git submodule add --depth 1 -b v2.5.0 https://github.com/hyperledger/fabric-protos.git protos/fabric-protos
git submodule update --init --recursive
```

2. Generate Python bindings (run from the repository root):

```bash
cd ./fabric-chaincode-python
PROTO_SRC=protos/fabric-protos bash scripts/gen_protos.sh
# generated files will be placed where the script is configured (e.g. fabric_protos_python/)
```

3. In CI: either regenerate and `git diff` against committed bindings to detect
	 drift, or regenerate in the build environment so wheel artifacts include the
	 bindings.

License
-------

`fabric-protos` is licensed under Apache-2.0. If you include `.proto` files or
generated bindings from that repository in your project, retain the original
license notice (do not remove the `LICENSE` files from the `fabric-protos`
source when copying). This is important if you plan to contribute or migrate the
project to Hyperledger Labs.
