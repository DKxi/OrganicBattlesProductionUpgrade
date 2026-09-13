import time
import threading
from typing import Dict, Any, Optional
from collections import deque


class MetricsRegistry:
    """
    Centralized, thread-safe metrics registry monitoring:
    1. Database query latency (total, avg, max, slow queries)
    2. Connection-pool utilization (checked in, checked out, overflow, utilization %)
    3. Track or boss bundle load time
    4. Cache hits and misses
    5. Cache memory consumption (bundle sizes, total bytes)
    6. JSON fallback count
    7. Ingestion validation failures
    8. Content-version mismatches
    9. Concurrent combat update conflicts
    """

    def __init__(self, max_recent_events: int = 100):
        self._lock = threading.Lock()
        self.max_recent_events = max_recent_events

        # 1. Database query latency metrics
        self._total_queries = 0
        self._total_query_time_ms = 0.0
        self._max_query_latency_ms = 0.0
        self._slow_queries_count = 0  # queries > 100ms
        self._recent_slow_queries = deque(maxlen=max_recent_events)

        # 6. JSON fallback count
        self._json_fallback_count = 0
        self._json_fallback_by_track: Dict[str, int] = {}

        # 7. Ingestion validation failures
        self._ingestion_validation_failures_count = 0
        self._recent_validation_failures = deque(maxlen=max_recent_events)

        # 8. Content-version mismatches
        self._content_version_mismatches_count = 0
        self._recent_version_mismatches = deque(maxlen=max_recent_events)

        # 9. Concurrent combat update conflicts
        self._combat_concurrency_conflicts_count = 0
        self._recent_combat_conflicts = deque(maxlen=max_recent_events)

    # --- 1. Database Query Latency ---
    def record_query_latency(self, duration_ms: float, statement: Optional[str] = None) -> None:
        with self._lock:
            self._total_queries += 1
            self._total_query_time_ms += duration_ms
            if duration_ms > self._max_query_latency_ms:
                self._max_query_latency_ms = duration_ms
            if duration_ms > 100.0:
                self._slow_queries_count += 1
                if statement:
                    self._recent_slow_queries.append({
                        "duration_ms": round(duration_ms, 2),
                        "statement": statement[:200],
                        "timestamp": int(time.time()),
                    })

    def get_query_latency_metrics(self) -> Dict[str, Any]:
        with self._lock:
            avg_ms = (self._total_query_time_ms / self._total_queries) if self._total_queries > 0 else 0.0
            return {
                "total_queries": self._total_queries,
                "avg_query_latency_ms": round(avg_ms, 2),
                "max_query_latency_ms": round(self._max_query_latency_ms, 2),
                "slow_queries_count": self._slow_queries_count,
                "recent_slow_queries": list(self._recent_slow_queries),
            }

    # --- 6. JSON Fallback Count ---
    def record_json_fallback(self, track_id: str) -> None:
        with self._lock:
            self._json_fallback_count += 1
            self._json_fallback_by_track[track_id] = self._json_fallback_by_track.get(track_id, 0) + 1

    def get_json_fallback_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_fallback_count": self._json_fallback_count,
                "by_track": dict(self._json_fallback_by_track),
            }

    # --- 7. Ingestion Validation Failures ---
    def record_ingestion_validation_failure(self, details: Dict[str, Any]) -> None:
        with self._lock:
            self._ingestion_validation_failures_count += 1
            entry = dict(details)
            entry["timestamp"] = int(time.time())
            self._recent_validation_failures.append(entry)

    def get_ingestion_validation_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_validation_failures": self._ingestion_validation_failures_count,
                "recent_failures": list(self._recent_validation_failures),
            }

    # --- 8. Content-Version Mismatches ---
    def record_content_version_mismatch(self, track_id: str, requested_version: str, active_version: str) -> None:
        with self._lock:
            self._content_version_mismatches_count += 1
            self._recent_version_mismatches.append({
                "track_id": track_id,
                "requested_version": requested_version,
                "active_version": active_version,
                "timestamp": int(time.time()),
            })

    def get_content_version_mismatch_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_version_mismatches": self._content_version_mismatches_count,
                "recent_mismatches": list(self._recent_version_mismatches),
            }

    # --- 9. Concurrent Combat Update Conflicts ---
    def record_combat_concurrency_conflict(self, session_id: Any, reason: str) -> None:
        with self._lock:
            self._combat_concurrency_conflicts_count += 1
            self._recent_combat_conflicts.append({
                "session_id": str(session_id),
                "reason": reason,
                "timestamp": int(time.time()),
            })

    def get_combat_conflict_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_concurrency_conflicts": self._combat_concurrency_conflicts_count,
                "recent_conflicts": list(self._recent_combat_conflicts),
            }

    # --- Central Observability Report ---
    def get_system_metrics(self) -> Dict[str, Any]:
        """Assembles all 9 monitored production telemetry dimensions."""
        from app.infrastructure.cache.shared_cache import shared_track_cache
        from app.infrastructure.database.engine import get_connection_pool_status

        cache_stats = shared_track_cache.stats()
        bundle_sizes = cache_stats.get("bundle_sizes_bytes", {})
        total_cache_bytes = sum(bundle_sizes.values())

        return {
            # 1. Database query latency
            "database_query_latency": self.get_query_latency_metrics(),
            # 2. Connection-pool utilization
            "connection_pool": get_connection_pool_status(),
            # 3. Track or boss bundle load time
            "bundle_load_time_ms": cache_stats.get("load_durations_ms", {}),
            # 4. Cache hits and misses
            "cache_hits_misses": {
                "hits": cache_stats.get("hits", 0),
                "misses": cache_stats.get("misses", 0),
                "hit_ratio": cache_stats.get("hit_ratio", 0.0),
                "evictions": cache_stats.get("evictions", 0),
            },
            # 5. Cache memory consumption
            "cache_memory_consumption": {
                "total_cache_bytes": total_cache_bytes,
                "total_cache_kb": round(total_cache_bytes / 1024, 2),
                "bundle_sizes_bytes": bundle_sizes,
                "cached_tracks": cache_stats.get("cached_tracks", []),
            },
            # 6. JSON fallback count
            "json_fallback": self.get_json_fallback_metrics(),
            # 7. Ingestion validation failures
            "ingestion_validation": self.get_ingestion_validation_metrics(),
            # 8. Content-version mismatches
            "content_version_mismatches": self.get_content_version_mismatch_metrics(),
            # 9. Concurrent combat update conflicts
            "combat_concurrency_conflicts": self.get_combat_conflict_metrics(),
        }

    def clear(self) -> None:
        """Reset metrics counters (useful for isolated tests)."""
        with self._lock:
            self._total_queries = 0
            self._total_query_time_ms = 0.0
            self._max_query_latency_ms = 0.0
            self._slow_queries_count = 0
            self._recent_slow_queries.clear()
            self._json_fallback_count = 0
            self._json_fallback_by_track.clear()
            self._ingestion_validation_failures_count = 0
            self._recent_validation_failures.clear()
            self._content_version_mismatches_count = 0
            self._recent_version_mismatches.clear()
            self._combat_concurrency_conflicts_count = 0
            self._recent_combat_conflicts.clear()


# Global singleton instance
metrics_registry = MetricsRegistry()
