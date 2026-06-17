"""A minimal async TTL cache with per-key locking.

Per-key locks prevent a cache stampede: when several requests miss the same key
at once (e.g. the chat path hitting a ticker the report is also fetching), only
one upstream call is made and the others await its result.
"""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, Hashable, TypeVar

T = TypeVar("T")


class TTLCache:
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: dict[Hashable, tuple[float, object]] = {}
        self._locks: dict[Hashable, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def get_or_set(
        self, key: Hashable, factory: Callable[[], Awaitable[T]]
    ) -> T:
        cached = self._fresh(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        lock = await self._lock_for(key)
        async with lock:
            # Re-check inside the lock: another coroutine may have filled it.
            cached = self._fresh(key)
            if cached is not None:
                return cached  # type: ignore[return-value]
            value = await factory()
            self._store[key] = (time.monotonic() + self._ttl, value)
            return value

    def _fresh(self, key: Hashable) -> object | None:
        hit = self._store.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        return None

    async def _lock_for(self, key: Hashable) -> asyncio.Lock:
        async with self._guard:
            return self._locks.setdefault(key, asyncio.Lock())

    def clear(self) -> None:
        self._store.clear()
        self._locks.clear()
