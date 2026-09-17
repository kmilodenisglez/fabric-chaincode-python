# fabric_contract_api — Contract API for Hyperledger Fabric (Python)

This package is the Python port of Hyperledger's
[`fabric-contract-api-go`](https://github.com/hyperledger/fabric-contract-api-go).
It builds on top of the existing `fabric_shim` package (the low-level
chaincode shim) to provide a high-level, contract-oriented programming
model where you declare contracts as plain Python classes and let the
framework handle argument marshalling, metadata generation, schema
validation and dispatch.

## Layout

```
src/fabric_contract_api/
├── __init__.py
├── contractapi/                  # High-level API used by application code
│   ├── __init__.py
│   ├── contract.py               # Contract base class + interfaces
│   ├── contract_chaincode.py     # ContractChaincode (implements Chaincode)
│   ├── system_contract.py        # Built-in metadata-serving contract
│   ├── transaction_context.py    # TransactionContext + ClientIdentity
│   └── utils/
│       ├── __init__.py
│       └── undefined_interface.py
├── internal/                     # Building blocks (mirrors Go's internal/)
│   ├── __init__.py
│   ├── contract_function.py      # Wraps a callable for dispatch
│   ├── transaction_handler.py    # Before/After/Unknown handlers
│   ├── types.py                  # Basic-type converters + schema snippets
│   ├── types_handler.py          # Static type validation
│   └── utils.py                  # Small helpers (string_in_slice, ...)
├── metadata/                     # Metadata dataclasses + JSON-schema helpers
│   ├── __init__.py
│   ├── metadata.py
│   ├── schema.py
│   └── schema/
│       └── schema.json           # Embedded JSON schema (from Go)
└── serializer/                   # Transaction serializers
    ├── __init__.py
    ├── transaction_serializer.py  # Abstract base
    └── json_transaction_serializer.py  # Default JSON serializer
```

## Quick start

```python
from src.fabric_contract_api import (
    Contract,
    ContractChaincode,
    TransactionContextInterface,
)


class SimpleContract(Contract):
    Name = "SimpleContract"

    async def create(self, ctx: TransactionContextInterface, key: str) -> None:
        if await ctx.get_stub().get_state(key):
            raise ValueError(f"key {key} already exists")
        await ctx.get_stub().put_state(key, b"Initialised")

    async def read(self, ctx: TransactionContextInterface, key: str) -> bytes:
        existing = await ctx.get_stub().get_state(key)
        if not existing:
            raise ValueError(f"key {key} does not exist")
        return existing

    def get_evaluate_transactions(self):
        return ["read"]


if __name__ == "__main__":
    cc = ContractChaincode.new_chaincode(SimpleContract())
    cc.start()  # Reads CHAINCODE_SERVER_ADDRESS / CHAINCODE_ID from env
```

## Mapping from Go to Python

| Go (`fabric-contract-api-go`)             | Python (`fabric_contract_api`)                       |
| ----------------------------------------- | ---------------------------------------------------- |
| `contractapi.ContractInterface`            | `contractapi.ContractInterface` (abc.ABC)            |
| `contractapi.IgnoreContractInterface`     | `contractapi.IgnoreContractInterface` (abc.ABC)      |
| `contractapi.EvaluationContractInterface` | `contractapi.EvaluationContractInterface` (abc.ABC)  |
| `contractapi.Contract`                    | `contractapi.Contract`                                |
| `contractapi.ContractChaincode`           | `contractapi.ContractChaincode`                      |
| `contractapi.NewChaincode(...)`           | `ContractChaincode.new_chaincode(...)`               |
| `contractapi.SystemContract`              | `contractapi.SystemContract`                          |
| `contractapi.TransactionContext`          | `contractapi.TransactionContext`                      |
| `contractapi.TransactionContextInterface` | `contractapi.TransactionContextInterface`             |
| `internal.ContractFunction`               | `internal.ContractFunction`                           |
| `internal.TransactionHandler`            | `internal.TransactionHandler`                         |
| `internal/types`                          | `internal/types`                                      |
| `internal/types_handler`                  | `internal/types_handler`                              |
| `metadata.ContractChaincodeMetadata`      | `metadata.ContractChaincodeMetadata`                  |
| `serializer.TransactionSerializer`        | `serializer.TransactionSerializer`                   |
| `serializer.JSONSerializer`               | `serializer.JSONSerializer`                           |

## Supported types

The JSON serializer understands the following Python types for both
parameters and return values:

| Python type                  | JSON schema produced                              |
| ---------------------------- | ------------------------------------------------ |
| `str`                        | `{"type": "string"}`                             |
| `bool`                       | `{"type": "boolean"}`                            |
| `int`                        | `{"type": "integer", "format": "int64"}`         |
| `float`                      | `{"type": "number", "format": "float"}`          |
| `bytes`, `bytearray`         | `{"type": "string", "format": "byte"}`            |
| `datetime.datetime`          | `{"type": "string", "format": "date-time"}`      |
| `list[T]` / `typing.List[T]` | `{"type": "array", "items": <schema-of-T>}`      |
| `dict[str, V]`               | `{"type": "object", "additionalProperties": ...}` |
| `typing.Any` / `object`      | `{}` (any value)                                  |
| dataclass                    | `{"$ref": "#/components/schemas/<ClassName>"}`    |
| Plain user-defined class     | `{"$ref": "#/components/schemas/<ClassName>"}`   |

## Function return conventions

A transaction function may return its result in any of three ways — the
contract API handles all of them:

1. **Raise an exception** — the simplest and most Pythonic form.  The
   exception's `str()` representation is sent back to the peer as an error
   response.
2. **Go-style tuple `(value, exception_or_None)`** — when the function's
   return annotation is `Tuple[T, Optional[Exception]]`.  If the exception
   slot is `None` the success value is used, otherwise the exception is
   propagated.
3. **Plain success value** — when the function returns a single value of
   the annotated success type.

Functions that take no parameters beyond the transaction context may omit
the return type annotation; their return value will be ignored.

## Calling conventions

The contract chaincode dispatches incoming transactions using the same
rules as the Go implementation:

* The first argument is `"<contract>:<function>"` (or just `"<function>"`
  to use the default contract).
* Remaining arguments are converted from strings to the function's
  parameter types by the active transaction serializer (JSONSerializer by
  default).
* If the function is not found in the contract, the contract's
  `UnknownTransaction` handler (if any) is called.
* `BeforeTransaction` is called *before* the named function; if it errors,
  the named function is skipped.
* `AfterTransaction` is called *after* the named function and receives
  the named function's success value; if it errors, its error is returned.

## Metadata

`ContractChaincode` automatically reflects over the registered contracts to
build a `ContractChaincodeMetadata` object — the same structure produced by
the Go implementation.  The metadata is then:

* merged with any user-supplied file at `META-INF/metadata.json` or
  `contract-metadata/metadata.json`,
* validated against the JSON schema shipped at
  `src/fabric_contract_api/metadata/schema/schema.json`,
* stored on the built-in `SystemContract` and exposed via the
  `org.hyperledger.fabric:get_metadata` transaction.

## Tests

Run the smoke tests with:

```bash
python -m pytest tests/test_contract_api.py -v
```

The tests use an in-memory `MockChaincodeStub` to exercise the dispatcher
without requiring a running Fabric peer.
