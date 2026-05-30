"""Lightweight TTL cache with LRU eviction.

Generic, zero-dependency cache suitable for asyncio cooperative scheduling.
Uses ``time.monotonic()`` (immune to NTP adjustments) and lazy expiry
(expired entries removed on access, not via background tasks).
"""

from __future__ import annotations

from collections import OrderedDict
from time import monotonic


class TTLCache[K, V]:
    """Thread-safe-for-asyncio TTL cache with bounded size.

    Parameters
    ----------
    ttl:
        Time-to-live in seconds.  Entries older than this are considered
        expired and silently removed on access.
    maxsize:
        Maximum number of entries.  When full, the *oldest-inserted*
        entry is evicted (LRU by insertion order, not by expiry).
    """

    def __init__(self, *, ttl: float, maxsize: int) -> None:
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._ttl = ttl
        self._maxsize = maxsize
        # OrderedDict preserves insertion order; move_to_end on access
        # keeps the oldest-inserted entry at the front for eviction.
        self._data: OrderedDict[K, tuple[float, V]] = OrderedDict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: K) -> V | None:
        """Return value if *key* exists and is not expired, else ``None``."""
        entry = self._data.get(key)
        if entry is None:
            return None
        ts, value = entry
        if monotonic() - ts > self._ttl:
            del self._data[key]
            return None
        # Move to end so it survives LRU eviction longer.
        self._data.move_to_end(key)
        return value

    def set(self, key: K, value: V) -> None:
        """Store *value* under *key* with the current monotonic timestamp.

        If the cache is at *maxsize*, the oldest-inserted entry is evicted
        first.  Updating an existing key refreshes its timestamp and moves
        it to the most-recent position.
        """
        if key in self._data:
            self._data.move_to_end(key)
        elif len(self._data) >= self._maxsize:
            # popitem(last=False) removes the *first* (oldest) item.
            self._data.popitem(last=False)
        self._data[key] = (monotonic(), value)

    def invalidate(self, key: K) -> None:
        """Remove *key* from the cache if present."""
        self._data.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        """Return ``True`` if *key* exists and is not expired."""
        entry = self._data.get(key)  # type: ignore[arg-type]
        if entry is None:
            return False
        ts, _ = entry
        if monotonic() - ts > self._ttl:
            # Lazy eviction — keep the dict clean.
            del self._data[key]  # type: ignore[arg-type]
            return False
        return True
