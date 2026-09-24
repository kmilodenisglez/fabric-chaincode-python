# Contributing to fabric-chaincode-python

We welcome contributions to the [Hyperledger Fabric](https://hyperledger-fabric.readthedocs.io) Project. There's always plenty to do!

If you have any questions about the project or how to contribute, you can find us in the [fabric-chaincode-python](https://discord.gg/hyperledger-fabric) channel on [Discord](https://discord.lfdecentralizedtrust.org/).

Here are a few guidelines to help you contribute successfully.

## Issues

All issues are tracked in the issues tab in GitHub. If you find a bug which we don't already know about, you can help us by creating a new issue describing the problem. Please include as much detail as possible to help us track down the cause. If you want to begin contributing code, looking through our open issues is a good way to start. Try looking for recent issues with detailed descriptions first, or ask us on Discord if you're unsure which issue to choose.

## Enhancements

Make sure you have the support of the Hyperledger Fabric community before investing a lot of effort in project enhancements. Please look up the [Fabric RFC](https://github.com/hyperledger/fabric-rfcs) process for large changes.

## Pull Requests

We use our own forks and [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow) to deliver changes to the code. Follow these steps to deliver your first pull request:

1. [Fork the repository](https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project) and create a new branch from `main`.
2. If you've added code that should be tested, add tests!
3. If you've added any new features or made breaking changes, update the documentation.
4. Ensure all the tests pass.
5. Include a descriptive message and the [Developer Certificate of Origin (DCO) sign-off](https://github.com/dcoapp/app#how-it-works) on all commit messages.
6. [Issue a pull request](https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project#making-a-pull-request)!
7. [GitHub Actions](https://github.com/hyperledger/fabric-chaincode-python/actions) builds must succeed before the pull request can be reviewed and coded.

## Coding Style

Please try to be consistent with the rest of the code. The project uses [ruff](https://docs.astral.sh/ruff/) for linting and [black](https://black.readthedocs.io/) for code formatting. You can run `python -m ruff check .` and `python -m black .` to check/format your code before submitting changes to avoid failing the build with formatting violations.

## Code of Conduct Guidelines

See our [Code of Conduct Guidelines](CODE_OF_CONDUCT.md).

## Maintainers

Should you have any questions or concerns, please reach out to one of the project's [Maintainers](MAINTAINERS.md).


## How to work with the Codebase

Some useful commands to help with building and testing:

```shell
# Run all tests
pytest -v

# Run linting
python -m ruff check .

# Format code
python -m black .

# Build a wheel
python -m build --sdist --wheel
```

You can also scan for vulnerabilities in dependencies:

```shell
make scan
```

## Hyperledger Fabric

See the
[Hyperledger Fabric contributors guide](http://hyperledger-fabric.readthedocs.io/en/latest/CONTRIBUTING.html) for more details, including other Hyperledger Fabric projects you may wish to contribute to.

---

[![Creative Commons License](https://i.creativecommons.org/l/by/4.0/88x31.png)](http://creativecommons.org/licenses/by/4.0/)
This work is licensed under a [Creative Commons Attribution 4.0 International License](http://creativecommons.org/licenses/by/4.0/).