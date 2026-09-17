# SPDX-License-Identifier: Apache-2.0
"""Asynchronous iterators for Fabric state / history / query results.

The contract API exposes three operations that return iterators over ledger
data:

* :func:`ChaincodeStub.get_state_by_range` / :func:`get_state_by_partial_composite_key`
  → :class:`StateQueryIterator`
* :func:`ChaincodeStub.get_query_result` (CouchDB rich queries)
  → :class:`QueryResultIterator` (same wire protocol as state queries)
* :func:`ChaincodeStub.get_history_for_key`
  → :class:`HistoryQueryIterator` (yields :class:`KeyModification` records)

Each iterator transparently pages through the peer's responses by sending
``QueryStateNext`` messages until the peer reports ``has_more == false``,
then closes the query with ``QueryStateClose`` when the iteration ends.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, List, Optional


class _QueryIteratorBase:
    """Common base for paged query iterators."""

    def __init__(self, handler, channel_id: str, tx_id: str,
                 initial_response, response_factory, parser):
        self._handler = handler
        self._channel_id = channel_id
        self._tx_id = tx_id
        self._response_factory = response_factory  # callable(msg_bytes) -> QueryResponse
        self._parser = parser  # callable(QueryResultBytes) -> parsed value
        self._buffer: List[Any] = []
        self._id: Optional[str] = None
        self._has_more: bool = False
        self._closed: bool = False
        self._consume(initial_response)

    def _consume(self, raw_msg) -> None:
        """Parse a peer QueryResponse message into buffer + pagination state."""
        if raw_msg is None:
            return
        resp = self._response_factory(raw_msg.payload)
        self._id = resp.id
        for qrb in resp.results:
            self._buffer.append(self._parser(qrb))
        self._has_more = bool(resp.has_more)

    async def __aiter__(self):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._buffer:
            return self._buffer.pop(0)
        if not self._has_more or self._id is None:
            await self._close()
            raise StopAsyncIteration
        # Request the next page from the peer.
        next_response = await self._handler.handle_query_state_next(
            self._id, self._channel_id, self._tx_id,
        )
        self._consume(next_response)
        if self._buffer:
            return self._buffer.pop(0)
        await self._close()
        raise StopAsyncIteration

    async def _close(self) -> None:
        if self._closed or self._id is None:
            self._closed = True
            return
        self._closed = True
        try:
            await self._handler.handle_query_state_close(
                self._id, self._channel_id, self._tx_id,
            )
        except Exception:
            # Best-effort close; iterators must not raise on close.
            pass

    async def aclose(self) -> None:
        """Explicit close — safe to call multiple times."""
        await self._close()


class StateQueryIterator(_QueryIteratorBase):
    """Iterates over (key, value) byte pairs returned by GetStateByRange."""


class QueryResultIterator(_QueryIteratorBase):
    """Iterates over rich-query (CouchDB) results."""


class HistoryQueryIterator(_QueryIteratorBase):
    """Iterates over :class:`KeyModification` records returned by GetHistoryForKey."""


__all__ = [
    "StateQueryIterator",
    "QueryResultIterator",
    "HistoryQueryIterator",
]
