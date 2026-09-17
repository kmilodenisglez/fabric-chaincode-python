# SPDX-License-Identifier: Apache-2.0
"""Internal helper utilities used throughout :mod:`fabric_contract_api`.

These helpers are the Python equivalent of the helpers in Go's
``fabric-contract-api-go/internal/utils`` package.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence


def string_in_slice(needle: str, haystack: Sequence[str]) -> bool:
    """Return ``True`` if *needle* is in *haystack*.

    Mirrors ``utils.StringInSlice`` from the Go implementation.
    """
    return needle in haystack


def slice_as_comma_sentence(items: Sequence[str]) -> str:
    """Format *items* as a comma-separated "and" sentence.

    Mirrors ``utils.SliceAsCommaSentence`` from the Go implementation, e.g.::

        ["a"]            -> "a"
        ["a", "b"]       -> "a and b"
        ["a", "b", "c"]  -> "a, b and c"
    """
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    head = ", ".join(items[:-1])
    return f"{head} and {items[-1]}"


def validate_errors_to_string(errors: Iterable[str]) -> str:
    """Convert a list of JSON-schema validation errors into a readable string.

    Mirrors ``utils.ValidateErrorsToString`` from the Go implementation.  The
    errors are sorted lexicographically and numbered 1..N.
    """
    sorted_errors: List[str] = sorted(str(e) for e in errors)
    if not sorted_errors:
        return ""
    return "\n".join(
        f"{i + 1}. {err}" for i, err in enumerate(sorted_errors)
    )


__all__ = [
    "string_in_slice",
    "slice_as_comma_sentence",
    "validate_errors_to_string",
]
