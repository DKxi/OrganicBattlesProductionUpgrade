import time
import sys
import zlib
import pickle
import logging
import threading
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from app.settings import settings
from app.infrastructure.cache.track_cache import BoundedTrackCache

logger = logging.getLogger("organicbattles.cache.shared")


class SharedTrackCacheManager:
    """
    Shared cache manager implementing Option A:
    - Bounded memory caching with TTL.
    - Versioned keys: (track_id, content_release_id).
    - Redis support with automatic fallback to local synchronized cache.
    - Distributed/concurrency rebuild locks to eliminate duplicate simultaneous builds (thundering herd).
    - Telemetry tracking: hit ratio, bundle size in bytes, load duration in ms.
    - Deployment cache warming for popular tracks.
    """

    def __init__(
        self,
        max_cached_tracks: int = 4,
        ttl_seconds: int = 3600,
        redis_url: Optional[str] = None,
    ):
        self.max_cached_tracks = max_cached_tracks
        self.ttl_seconds = ttl_seconds
        self.redis_url = redis_url

        # Primary in-memory tier (bounded LRU with TTL)
        self.local_cache = BoundedTrackCache(max_size=max_cached_tracks, ttl_seconds=ttl_seconds)

        # Thread-safe rebuild locks per track
        self._rebuild_locks: Dict[str, threading.Lock] = {}
        self._rebuild_locks_mutex = threading.Lock()

        # Telemetry metrics
        self._hits = 0
        self._misses = 0
        self._load_durations_ms: Dict[str, float] = {}
        self._bundle_sizes_bytes: Dict[str, int] = {}

        # Content source, version, and fallback status telemetry
        self._content_sources: Dict[str, str] = {}
        self._content_versions: Dict[str, str] = {}
        self._fallback_statuses: Dict[str, str] = {}
        self._database_available: bool = True

        # Redis connection setup
        self._redis_client = None
        if self.redis_url:
            self._init_redis()

    def _init_redis(self) -> None:
        try:
            import redis
            client = redis.Redis.from_url(
                self.redis_url,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
            )
            client.ping()
            self._redis_client = client
            logger.info("SharedTrackCacheManager successfully connected to Redis: %s", self.redis_url)
        except Exception as exc:
            logger.warning("Redis connection failed, continuing with local shared cache fallback: %s", exc)
            self._redis_client = None

    @property
    def backend(self) -> str:
        return "redis" if self._redis_client is not None else "memory"

    def get_track_rebuild_lock(self, track_id: str) -> threading.Lock:
        """Get or create reentrant/thread lock for rebuilding a specific track."""
        with self._rebuild_locks_mutex:
            if track_id not in self._rebuild_locks:
                self._rebuild_locks[track_id] = threading.Lock()
            return self._rebuild_locks[track_id]

    def format_cache_key(self, track_id: str, release_id: Optional[str] = None) -> str:
        """Construct versioned cache key: {track_id}:v{release_id}."""
        rel = release_id or "default"
        return f"{track_id}:{rel}"

    def get_content_version(self, track_id: str, db: Optional[Any] = None) -> str:
        """
        Resolve current active release ID for a track.
        Checks DB ContentRelease, fallback to Redis or default v1.
        """
        # 1. Try checking Redis version key if active
        if self._redis_client is not None:
            try:
                cached_ver = self._redis_client.get(f"content_release:{track_id}")
                if cached_ver:
                    return cached_ver.decode("utf-8") if isinstance(cached_ver, bytes) else str(cached_ver)
            except Exception as e:
                logger.debug("Redis get_content_version note: %s", e)

        # 2. Try checking active ContentRelease from database
        try:
            from app.infrastructure.database.releases_repo import ReleasesRepository
            if db is not None:
                repo = ReleasesRepository(db)
                active = repo.get_active_release(track_id)
                if active:
                    return active.id
            else:
                from app.infrastructure.database.engine import SessionLocal
                with SessionLocal() as session:
                    repo = ReleasesRepository(session)
                    active = repo.get_active_release(track_id)
                    if active:
                        return active.id
        except Exception as exc:
            logger.debug("Database content version lookup note: %s", exc)

        return f"{track_id}_v1"

    def increment_content_version(self, track_id: str) -> str:
        """
        Increment content release version across the cluster.
        Updates Redis key and invalidates local cache.
        """
        new_ver_id = f"{track_id}_v{int(time.time())}"
        if self._redis_client is not None:
            try:
                self._redis_client.set(f"content_release:{track_id}", new_ver_id, ex=self.ttl_seconds)
            except Exception as e:
                logger.warning("Redis increment_content_version failed: %s", e)

        self.invalidate_track(track_id)
        return new_ver_id

    def get(self, track_id: str, release_id: Optional[str] = None) -> Optional[Any]:
        """Look up bundle by (track_id, release_id) across local and Redis tiers."""
        cache_key = self.format_cache_key(track_id, release_id)

        # 1. Local Bounded Cache check
        if cache_key in self.local_cache:
            self._hits += 1
            return self.local_cache[cache_key]

        # 2. Redis check if available
        if self._redis_client is not None:
            try:
                raw = self._redis_client.get(f"bundle:{cache_key}")
                if raw:
                    decompressed = zlib.decompress(raw)
                    bundle = pickle.loads(decompressed)
                    # Populate local tier
                    self.local_cache[cache_key] = bundle
                    self._hits += 1
                    return bundle
            except Exception as exc:
                logger.debug("Redis bundle retrieval note: %s", exc)

        self._misses += 1
        return None

    def set(self, track_id: str, release_id: Optional[str], bundle: Any, load_duration_ms: float = 0.0) -> None:
        """Cache bundle in local bounded cache and Redis with TTL and telemetry."""
        cache_key = self.format_cache_key(track_id, release_id)
        self.local_cache[cache_key] = bundle

        # Measure / estimate bundle size
        try:
            pickled = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = zlib.compress(pickled, level=3)
            size_bytes = len(compressed)
            self._bundle_sizes_bytes[track_id] = size_bytes

            if self._redis_client is not None:
                self._redis_client.setex(f"bundle:{cache_key}", self.ttl_seconds, compressed)
        except Exception as exc:
            # Fallback size estimation
            self._bundle_sizes_bytes[track_id] = sys.getsizeof(bundle)
            logger.debug("Bundle serialization size note: %s", exc)

        self._load_durations_ms[track_id] = round(load_duration_ms, 2)

    def invalidate_track(self, track_id: str) -> None:
        """Invalidate all cached bundles for a track across tiers."""
        # Evict matching local keys
        keys_to_evict = [k for k in list(self.local_cache.keys()) if k.startswith(f"{track_id}:") or k == track_id]
        for k in keys_to_evict:
            self.local_cache.pop(k, None)

        # Evict from Redis if connected
        if self._redis_client is not None:
            try:
                pattern = f"bundle:{track_id}:*"
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as exc:
                logger.debug("Redis invalidate_track note: %s", exc)

    def clear(self) -> None:
        """Clear all cached bundles across tiers."""
        self.local_cache.clear()
        self._content_sources.clear()
        self._content_versions.clear()
        self._fallback_statuses.clear()
        self._database_available = True
        if self._redis_client is not None:
            try:
                keys = self._redis_client.keys("bundle:*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as exc:
                logger.debug("Redis clear note: %s", exc)

    def warm_tracks(self, root_dir: Path, track_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Warm popular tracks during deployment/startup:
        Ensures content is preloaded into cache before players encounter cold-start latency.
        """
        from app.domain.content.loader import load_track_bundle

        if not track_ids:
            tracks_str = settings.popular_tracks_to_warm or "default"
            track_ids = [t.strip() for t in tracks_str.split(",") if t.strip()]

        results = {}
        for tid in track_ids:
            start_t = time.time()
            rel_id = self.get_content_version(tid)
            # Rebuild lock prevents race condition during warmup
            lock = self.get_track_rebuild_lock(tid)
            with lock:
                bundle = self.get(tid, rel_id)
                if not bundle:
                    bundle = load_track_bundle(root_dir, tid)
                    duration_ms = (time.time() - start_t) * 1000.0
                    self.set(tid, rel_id, bundle, load_duration_ms=duration_ms)
                    results[tid] = {"status": "warmed", "duration_ms": round(duration_ms, 2), "release_id": rel_id}
                else:
                    results[tid] = {"status": "already_cached", "release_id": rel_id}

        logger.info("Deployment cache warming complete: %s", results)
        return results

    def stats(self) -> Dict[str, Any]:
        """Comprehensive cache performance and sizing telemetry."""
        total_requests = self._hits + self._misses
        hit_ratio = round(self._hits / total_requests, 4) if total_requests > 0 else 0.0

        return {
            "backend": self.backend,
            "size": len(self.local_cache),
            "max_size": self.max_cached_tracks,
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": hit_ratio,
            "evictions": self.local_cache.stats().get("evictions", 0),
            "load_durations_ms": dict(self._load_durations_ms),
            "bundle_sizes_bytes": dict(self._bundle_sizes_bytes),
            "cached_tracks": list(self.local_cache.keys()),
        }

    def record_content_status(
        self,
        track_id: str,
        source: str,
        version: str,
        fallback_status: str,
        database_available: bool = True,
    ) -> None:
        """Record content source, version, and fallback status for health tracking."""
        self._content_sources[track_id] = source
        self._content_versions[track_id] = version
        self._fallback_statuses[track_id] = fallback_status
        self._database_available = database_available

    def get_content_status(self, track_id: str) -> Dict[str, Any]:
        """Get the recorded status for a specific track."""
        return {
            "source": self._content_sources.get(track_id, "unknown"),
            "version": self._content_versions.get(track_id, "unknown"),
            "fallback_status": self._fallback_statuses.get(track_id, "unknown"),
            "status": "degraded" if self._fallback_statuses.get(track_id) in ("cache_degraded", "json_fallback") else "healthy",
            "release_id": self._content_versions.get(track_id, "unknown"),
        }

    def is_degraded(self) -> bool:
        """Check if any track is serving degraded fallback or database is down."""
        if not self._database_available:
            return True
        return any(fb in ("cache_degraded", "json_fallback") for fb in self._fallback_statuses.values())

    def get_any_validated(self, track_id: str) -> Optional[Tuple[str, Any]]:
        """Look up any validated cached bundle for track_id in local cache or Redis."""
        # 1. Check local_cache for matching track_id prefix
        for key in list(self.local_cache.keys()):
            if key == track_id or key.startswith(f"{track_id}:"):
                bundle = self.local_cache.get(key)
                if bundle is not None:
                    version = key.split(":", 1)[1] if ":" in key else "cached"
                    return version, bundle

        # 2. Check Redis if available
        if self._redis_client is not None:
            try:
                pattern = f"bundle:{track_id}:*"
                keys = self._redis_client.keys(pattern)
                if keys:
                    first_key = keys[0].decode("utf-8") if isinstance(keys[0], bytes) else str(keys[0])
                    raw = self._redis_client.get(first_key)
                    if raw:
                        decompressed = zlib.decompress(raw)
                        bundle = pickle.loads(decompressed)
                        version = first_key.split(":")[-1]
                        return version, bundle
            except Exception as exc:
                logger.debug("Redis get_any_validated note: %s", exc)

        return None

    def has_any_validated_cache(self) -> bool:
        """Returns True if any track bundles are currently cached in memory or Redis."""
        if len(self.local_cache) > 0:
            return True
        if self._redis_client is not None:
            try:
                keys = self._redis_client.keys("bundle:*")
                if keys:
                    return True
            except Exception:
                pass
        return False

    def get_health_metrics(self) -> Dict[str, Any]:
        """Comprehensive health information and metrics for internal diagnostics."""
        if not self._database_available:
            if self.has_any_validated_cache():
                readiness = "degraded"
            else:
                readiness = "unavailable"
        elif any(fb in ("cache_degraded", "json_fallback") for fb in self._fallback_statuses.values()):
            readiness = "degraded"
        else:
            readiness = "ready"

        overall_fallback = "none"
        if any(fb == "unavailable" for fb in self._fallback_statuses.values()):
            overall_fallback = "unavailable"
        elif any(fb == "cache_degraded" for fb in self._fallback_statuses.values()):
            overall_fallback = "cache_degraded"
        elif any(fb == "json_fallback" for fb in self._fallback_statuses.values()):
            overall_fallback = "json_fallback"

        return {
            "readiness": readiness,
            "database_available": self._database_available,
            "has_cached_content": self.has_any_validated_cache(),
            "degraded_mode": readiness == "degraded",
            "overall_fallback": overall_fallback,
            "allow_json_fallback": settings.allow_json_fallback,
            "content_sources": dict(self._content_sources),
            "content_versions": dict(self._content_versions),
            "fallback_statuses": dict(self._fallback_statuses),
            "cache_stats": self.stats(),
        }


# Global shared cache manager instance
shared_track_cache = SharedTrackCacheManager(
    max_cached_tracks=settings.max_cached_tracks,
    ttl_seconds=settings.track_cache_ttl_seconds,
    redis_url=settings.redis_url,
)
