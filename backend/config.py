"""
Centralised application configuration.
All settings are read from environment variables (or a .env file).
"""
import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings  # pyre-ignore[21]
except ImportError:
    from pydantic import BaseSettings  # type: ignore


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────
    app_name: str = "AI Cloud Cost Optimizer"
    app_version: str = "3.0.0"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = "sqlite:///./cloud_cost.db"

    # ── JWT Auth ─────────────────────────────────────────────────────
    jwt_secret_key: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    credential_encryption_key: Optional[str] = None

    # ── AWS ──────────────────────────────────────────────────────────
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "us-east-1"
    aws_profile: Optional[str] = None
    # Comma-separated list of linked account IDs to aggregate
    aws_linked_accounts: Optional[str] = None

    # ── GCP ──────────────────────────────────────────────────────────
    # Path to GCP service-account JSON key
    google_application_credentials: Optional[str] = None
    gcp_project_id: Optional[str] = None
    gcp_billing_account_id: Optional[str] = None

    # ── Azure ────────────────────────────────────────────────────────
    azure_subscription_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None

    # ── Kafka ────────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_cost_topic: str = "cloud-cost-events"
    kafka_group_id: str = "cost-optimizer-consumers"

    # ── Redis / Celery ───────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Budget Engine ────────────────────────────────────────────────
    default_alert_threshold_pct: float = 0.80  # 80 % of budget triggers alert

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance used throughout the application
settings = Settings()
