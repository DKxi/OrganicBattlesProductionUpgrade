import time
import threading
from collections import OrderedDict
from collections.abc import MutableMapping
from typing import Any, Dict, Iterator, Tuple


class BoundedTrackCache(MutableMapping):
    """
    Thread-safe, bounded LRU cache with TTL expiration for ContentBundle objects.
    Enforces a strict upper bound on in-memory track bundles to prevent
    unbounded memory growth across multiple Uvicorn workers and replicas.
    """

    def __init__(self, max_size: int = 4, ttl_seconds: int = 3600):
        self.max_size = max(1, int(max_size))
        self.ttl_seconds = max(0, int(ttl_seconds))
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @staticmethod
    def _normalize_key(key: Any) -> str:
        s_key = str(key)
        if s_key.startswith("track:"):
            return s_key[6:]
        return s_key

    def _is_expired(self, timestamp: float) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return (time.time() - timestamp) > self.ttl_seconds

    def __getitem__(self, key: Any) -> Any:
        norm_key = self._normalize_key(key)
        with self._lock:
            if norm_key in self._cache:
                val, ts = self._cache[norm_key]
                if self._is_expired(ts):
                    del self._cache[norm_key]
                    self._evictions += 1
                    self._misses += 1
                    raise KeyError(key)
                # Move to end to mark as recently used
                self._cache.move_to_end(norm_key)
                self._hits += 1
                return val
            self._misses += 1
            raise KeyError(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        norm_key = self._normalize_key(key)
        with self._lock:
            if norm_key in self._cache:
                self._cache.move_to_end(norm_key)
            else:
                # Evict least recently used if at or over capacity
                while len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                    self._evictions += 1
            self._cache[norm_key] = (value, time.time())

    def __delitem__(self, key: Any) -> None:
        norm_key = self._normalize_key(key)
        with self._lock:
            del self._cache[norm_key]

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            # Clean expired on iteration
            self._purge_expired()
            return iter(list(self._cache.keys()))

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired()
            return len(self._cache)

    def __contains__(self, key: object) -> bool:
        norm_key = self._normalize_key(key)
        with self._lock:
            if norm_key not in self._cache:
                return False
            _, ts = self._cache[norm_key]
            if self._is_expired(ts):
                del self._cache[norm_key]
                self._evictions += 1
                return False
            return True

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key: Any, *args: Any) -> Any:
        norm_key = self._normalize_key(key)
        with self._lock:
            if norm_key in self._cache:
                val, _ = self._cache.pop(norm_key)
                return val
            if args:
                return args[0]
            raise KeyError(key)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def _purge_expired(self) -> None:
        if self.ttl_seconds <= 0:
            return
        now = time.time()
        expired_keys = [k for k, (_, ts) in self._cache.items() if (now - ts) > self.ttl_seconds]
        for k in expired_keys:
            self._cache.pop(k, None)
            self._evictions += 1

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._purge_expired()
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "cached_tracks": list(self._cache.keys()),
            }
