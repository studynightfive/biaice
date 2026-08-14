"""Bounded dependency probes used by the public readiness endpoint."""

from __future__ import annotations

import json
import socket
import urllib.request
from collections.abc import Callable

from redis import Redis
from sqlalchemy import create_engine, text

from biaice.api.health import ComponentHealth
from biaice.core.config import Settings


def _down(name: str, exc: Exception) -> ComponentHealth:
    return ComponentHealth(name=name, status="DOWN", detail=type(exc).__name__)


def build_readiness_checks(
    settings: Settings,
) -> tuple[Callable[[], ComponentHealth], ...]:
    if settings.environment in {"test", "contract"}:
        return ()

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        connect_args={"connect_timeout": 2},
    )
    broker = Redis.from_url(
        settings.redis_broker_url,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )
    cache = Redis.from_url(
        settings.redis_cache_url,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )

    def database() -> ComponentHealth:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            return ComponentHealth(name="postgres_migrations", status="UP")
        except Exception as exc:  # pragma: no cover - exercised by Compose smoke
            return _down("postgres_migrations", exc)

    def redis_broker() -> ComponentHealth:
        try:
            if broker.ping() is not True:
                raise RuntimeError("unexpected Redis PING response")
            return ComponentHealth(name="redis_broker", status="UP")
        except Exception as exc:  # pragma: no cover - exercised by Compose smoke
            return _down("redis_broker", exc)

    def redis_cache() -> ComponentHealth:
        try:
            if cache.ping() is not True:
                raise RuntimeError("unexpected Redis PING response")
            return ComponentHealth(name="redis_cache", status="UP")
        except Exception as exc:  # pragma: no cover - exercised by Compose smoke
            return _down("redis_cache", exc)

    def oidc_jwks() -> ComponentHealth:
        if not settings.oidc_jwks_url:
            return ComponentHealth(
                name="oidc_jwks", status="DOWN", detail="not_configured"
            )
        try:
            with urllib.request.urlopen(settings.oidc_jwks_url, timeout=2) as response:
                payload = json.load(response)
            if not isinstance(payload.get("keys"), list) or not payload["keys"]:
                raise ValueError("JWKS contains no keys")
            return ComponentHealth(name="oidc_jwks", status="UP")
        except Exception as exc:  # pragma: no cover - exercised by Compose smoke
            return _down("oidc_jwks", exc)

    def minio() -> ComponentHealth:
        url = settings.minio_endpoint.rstrip("/") + "/minio/health/ready"
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status != 200:
                    raise RuntimeError("MinIO readiness was not 200")
            return ComponentHealth(name="minio", status="UP")
        except Exception as exc:  # pragma: no cover - exercised by Compose smoke
            return _down("minio", exc)

    def clamav() -> ComponentHealth:
        try:
            with socket.create_connection(
                (settings.clamav_host, settings.clamav_port), timeout=2
            ) as connection:
                connection.sendall(b"PING\n")
                response = connection.recv(16)
            if b"PONG" not in response:
                raise RuntimeError("ClamAV did not return PONG")
            return ComponentHealth(name="clamav", status="UP")
        except Exception as exc:  # pragma: no cover - exercised by Compose smoke
            return _down("clamav", exc)

    return database, redis_broker, redis_cache, oidc_jwks, minio, clamav
