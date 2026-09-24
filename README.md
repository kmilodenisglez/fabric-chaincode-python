# fabric-chaincode-python

[![Lifecycle](https://img.shields.io/badge/lifecycle-experimental- orange.svg)](https://github.com/hyperledger/fabric-chaincode-python/blob/main/lifecycle.md)
[![Python Version](https://img.shields.io/pypi/pyversions/fabric-chaincode-python.svg)](https://pypi.org/project/fabric-chaincode-python/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Actions](https://github.com/hyperledger/fabric-chaincode-python/workflows/CI/badge.svg)](https://github.com/hyperledger/fabric-chaincode-python/actions?query=workflow%3ACI)
[![GitHub Release](https://img.shields.io/github/v/release/hyperledger/fabric-chaincode-python.svg)](https://github.com/hyperledger/fabric-chaincode-python/releases)

# Hyperledger Fabric Chaincode shim and Contract API for Python

This repository provides the Python implementation of Hyperledger Fabric chaincode shim and contract API. Chaincodes (smart contracts) can be written in Python to run inside Hyperledger Fabric peers.

## Documentation

- API documentation: https://hyperledger.github.io/fabric-chaincode-python/
- Full Documentation on Hyperledger Fabric: https://hyperledger-fabric.readthedocs.io/
- Samples repository: https://github.com/hyperledger/fabric-samples
- Quick-start tutorial: TUTORIAL.md

## Compatibility

For details on what Python versions and Hyperledger Fabric versions can be used, see the [COMPATIBILITY.md](COMPATIBILITY.md).

## npm Shrinkwrap

Strongly recommended to create a `requirements.txt` file after testing and before putting your contract into production.

## Contributing

If you are interested in contributing updates to this project, please start with the [contributing guide](CONTRIBUTING.md).

There is also a [release guide](RELEASING.md) describing the process for publishing new versions.

## Build Status

CI runs with Python 3.11 on `main` and `release-*` branches, and on pull requests.