"""Process configuration with conservative, fail-closed defaults."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    A fresh checkout is deliberately synthetic-only. Merely setting
    ``real_data_mode_requested`` or ``byok_enabled`` never proves a gate; a
    machine-verifiable assessment must also be supplied by infrastructure.
    """

    model_config = SettingsConfigDict(
        env_prefix="BIAICE_",
        env_file=None,
        extra="ignore",
        case_sensitive=False,
    )

    application_name: str = "标策 AI API"
    application_version: str = "0.1.0"
    environment: Literal["development", "test", "contract", "production"] = "development"
    deployment_profile: Literal["synthetic_http", "secure_https"] = "synthetic_http"
    api_prefix: str = "/api/v1"
    public_origin: str = "https://biaice.local:8443"

    database_url: str = "postgresql+psycopg://biaice@postgres/biaice"
    redis_broker_url: str = "redis://redis-broker:6379/0"
    redis_cache_url: str = "redis://redis-cache:6379/0"
    minio_endpoint: str = "http://minio:9000"
    clamav_host: str = "clamav"
    clamav_port: int = 3310
    openbao_addr: str = "http://openbao:8200"

    oidc_issuer: str | None = None
    oidc_audience: str = "biaice-api"
    oidc_jwks_url: str | None = None
    allow_test_auth: bool = False
    test_auth_secret: SecretStr | None = None

    real_data_mode_requested: bool = False
    byok_enabled: bool = False
    gate_evidence_hmac_key: SecretStr | None = None
    cursor_hmac_key: SecretStr | None = None
    trusted_request_id_header: bool = True
    trust_gateway_forwarded_headers: bool = True

    audit_sink_required: bool = True
    audit_anchor_required: bool = True
    migrations_required: bool = True

    @model_validator(mode="after")
    def reject_unsafe_profiles(self) -> "Settings":
        if self.environment == "production" and self.deployment_profile != "secure_https":
            raise ValueError("production requires secure_https deployment_profile")
        if (
            self.real_data_mode_requested or self.byok_enabled
        ) and self.deployment_profile != "secure_https":
            raise ValueError("real data and BYOK are forbidden in synthetic_http profile")
        if self.allow_test_auth and self.environment != "test":
            raise ValueError("test authentication is only permitted in the test environment")
        if not 1 <= self.clamav_port <= 65535:
            raise ValueError("clamav_port must be a valid TCP port")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
