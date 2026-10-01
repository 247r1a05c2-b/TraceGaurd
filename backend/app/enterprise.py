from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

try:
    import redis
except Exception:
    redis = None

from .database import database_status
from .monitoring import clients
from .store import store

REQUEST_LATENCY = Histogram("tracegaurd_http_request_duration_seconds", "HTTP request duration", ["method", "path"])
ACTIVE_REQUESTS = Gauge("tracegaurd_http_active_requests", "Requests currently in flight")
CACHE_HITS = Counter("tracegaurd_cache_hits_total", "Cache hits", ["namespace"])
CACHE_MISSES = Counter("tracegaurd_cache_misses_total", "Cache misses", ["namespace"])
MONITORED_CLIENTS = Gauge("tracegaurd_monitored_clients", "Active monitored clients")
ACTIVE_INCIDENTS = Gauge("tracegaurd_active_incidents", "Known incidents")


class EnterpriseCache:
    def __init__(self) -> None:
        self.redis_url = os.getenv("REDIS_URL", "").strip()
        self.redis_client = None
        if self.redis_url and redis is not None:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=0.5,
                    socket_timeout=0.5,
                )
                self.redis_client.ping()
            except Exception:
                self.redis_client = None
        self._memory: dict[str, tuple[float, str]] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str, namespace: str = "default"):
        value = None
        if self.redis_client is not None:
            try:
                value = self.redis_client.get(key)
            except Exception:
                self.redis_client = None
        if value is None:
            with self._lock:
                item = self._memory.get(key)
                if item and item[0] > time.time():
                    value = item[1]
                elif item:
                    self._memory.pop(key, None)
        if value is None:
            self._misses += 1
            CACHE_MISSES.labels(namespace=namespace).inc()
            return None
        self._hits += 1
        CACHE_HITS.labels(namespace=namespace).inc()
        try:
            return json.loads(value)
        except Exception:
            return value

    def set(self, key: str, value, ttl: int = 10) -> None:
        encoded = json.dumps(value, default=str, separators=(",", ":"))
        if self.redis_client is not None:
            try:
                self.redis_client.setex(key, ttl, encoded)
                return
            except Exception:
                self.redis_client = None
        with self._lock:
            self._memory[key] = (time.time() + ttl, encoded)

    def delete_prefix(self, prefix: str) -> None:
        if self.redis_client is not None:
            try:
                keys = list(self.redis_client.scan_iter(match=f"{prefix}*"))
                if keys:
                    self.redis_client.delete(*keys)
            except Exception:
                pass
        with self._lock:
            for key in list(self._memory):
                if key.startswith(prefix):
                    self._memory.pop(key, None)

    def status(self) -> dict:
        redis_ok = False
        if self.redis_client is not None:
            try:
                redis_ok = bool(self.redis_client.ping())
            except Exception:
                redis_ok = False
        total = self._hits + self._misses
        return {
            "backend": "redis" if redis_ok else "memory",
            "distributed": redis_ok,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / max(1, total), 4),
        }


cache = EnterpriseCache()


class RateLimiter:
    def __init__(self) -> None:
        self.limit = max(30, int(os.getenv("RATE_LIMIT_PER_MINUTE", "240")))
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        cutoff = now - 60
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            if len(self._hits) > 5000:
                stale = [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]
                for stale_key in stale[:1000]:
                    self._hits.pop(stale_key, None)
            return True


rate_limiter = RateLimiter()


def _patch_cached_routes(app) -> None:
    for route in app.routes:
        if route.path == "/api/v1/clients" and "GET" in getattr(route, "methods", set()):
            original = route.endpoint

            def cached_clients(engineer: str, original=original):
                cached = cache.get("tg:clients", "clients")
                if cached is not None:
                    return cached
                result = original(engineer)
                cache.set("tg:clients", result, ttl=5)
                return result

            route.endpoint = cached_clients
            route.dependant.call = cached_clients
        elif route.path == "/api/v1/incidents" and "GET" in getattr(route, "methods", set()):
            original = route.endpoint

            def cached_incidents(engineer: str, original=original):
                cached = cache.get("tg:incidents", "incidents")
                if cached is not None:
                    return cached
                result = original(engineer)
                cache.set("tg:incidents", result, ttl=5)
                return result

            route.endpoint = cached_incidents
            route.dependant.call = cached_incidents
        elif route.path == "/api/v1/metrics" and "GET" in getattr(route, "methods", set()):
            original = route.endpoint

            def cached_metrics(engineer: str, original=original):
                cached = cache.get("tg:metrics", "metrics")
                if cached is not None:
                    return cached
                result = original(engineer)
                cache.set("tg:metrics", result, ttl=3)
                return result

            route.endpoint = cached_metrics
            route.dependant.call = cached_metrics


def install_enterprise(app) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

    @app.middleware("http")
    async def enterprise_middleware(request: Request, call_next):
        started = time.perf_counter()
        path = request.url.path
        if path not in {"/health", "/health/live", "/health/ready", "/metrics"}:
            client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
            if not rate_limiter.allow(client_ip):
                return PlainTextResponse("rate limit exceeded", status_code=429, headers={"Retry-After": "60"})
        request_id = request.headers.get("x-request-id") or uuid4().hex
        ACTIVE_REQUESTS.inc()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
            return response
        finally:
            ACTIVE_REQUESTS.dec()
            REQUEST_LATENCY.labels(method=request.method, path=path).observe(time.perf_counter() - started)

    @app.get("/health/live", include_in_schema=False)
    def liveness():
        return {"status": "alive", "service": "tracegaurd-api", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.get("/health/ready", include_in_schema=False)
    def readiness():
        db = database_status()
        ready = db.get("status") == "CONNECTED"
        payload = {"status": "ready" if ready else "not_ready", "database": db, "cache": cache.status(), "timestamp": datetime.now(timezone.utc).isoformat()}
        if not ready:
            raise HTTPException(status_code=503, detail=payload)
        return payload

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics():
        MONITORED_CLIENTS.set(len(clients))
        ACTIVE_INCIDENTS.set(len(store.incidents()))
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/enterprise/status")
    def enterprise_status():
        return {
            "edition": "TraceGaurd Enterprise",
            "scalability": {"stateless_api": True, "recommended_replicas": 3, "horizontal_autoscaling": True},
            "database": database_status(),
            "cache": cache.status(),
            "monitoring": {"prometheus": True, "metrics_endpoint": "/metrics", "request_tracing": True},
            "reliability": {"liveness": "/health/live", "readiness": "/health/ready", "graceful_failover": True},
            "security": {"rate_limit_per_minute": rate_limiter.limit, "security_headers": True},
        }

    _patch_cached_routes(app)
