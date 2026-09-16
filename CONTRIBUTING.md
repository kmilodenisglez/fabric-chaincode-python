# Contributing

This project follows the Hyperledger contribution requirements. Please read this file before contributing.

Signed-off-by / DCO
--------------------

This repository uses the Developer Certificate of Origin (DCO). All commits must be signed off using the `Signed-off-by:` trailer.

To sign off your commits locally, run:

```bash
git commit -s -m "Your commit message"
# or when amending
git commit --amend -s --no-edit
```

The sign-off will add a line like:

```
Signed-off-by: Your Name <you@example.com>
```

Make sure your Git `user.name` and `user.email` are configured correctly:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Protobuf bindings
--------------------

Bindings come from PyPI (`hyperledger-fabric-protos`) via `requirements.txt` - no extra steps needed.

If you need to test against unreleased `fabric-protos` changes, see `PROTOS.md` (`scripts/install_fabric_protos.sh` and `scripts/gen_protos.sh`).


Licensing
---------

This project is licensed under the Apache-2.0 license. By contributing you agree to license your contributions under the same terms.
