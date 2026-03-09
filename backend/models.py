from sqlalchemy import (  # pyre-ignore[21]
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship  # pyre-ignore[21]
from database import Base  # pyre-ignore[21]
import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Multi-Tenant Organization Models
# ─────────────────────────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, index=True)  # e.g. "acme-corp"
    plan = Column(String, default="free")           # free, pro, enterprise
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="organization", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    cloud_provider = Column(String, default="AWS")   # AWS | GCP | Azure | Multi
    description = Column(Text, default="")
    tags = Column(String, default="")               # JSON string of tags
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="projects")
    budgets = relationship("Budget", back_populates="project", cascade="all, delete-orphan")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    monthly_limit = Column(Float, nullable=False)       # USD
    alert_threshold_pct = Column(Float, default=0.80)   # 0.80 = 80 %
    period_start = Column(DateTime, default=datetime.datetime.utcnow)
    active = Column(Boolean, default=True)
    cloud_provider = Column(String, default="All")

    organization = relationship("Organization", back_populates="budgets")
    project = relationship("Project", back_populates="budgets")


# ─────────────────────────────────────────────────────────────────────────────
# Original Models (preserved)
# ─────────────────────────────────────────────────────────────────────────────

class CloudResource(Base):
    __tablename__ = "cloud_resources"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, index=True)
    resource_id = Column(String, unique=True, index=True)
    region = Column(String)
    provider = Column(String, default="AWS")     # NEW — cloud provider tag
    account_id = Column(String, default="")      # NEW — linked account / subscription
    status = Column(String)
    monthly_cost = Column(Float, default=0.0)
    cpu_utilization = Column(Float, default=0.0)


class CostAnomaly(Base):
    __tablename__ = "cost_anomalies"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, index=True)
    anomaly_date = Column(DateTime, default=datetime.datetime.utcnow)
    expected_cost = Column(Float)
    actual_cost = Column(Float)
    severity = Column(String)    # low, medium, high, critical
    provider = Column(String, default="AWS")


class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String, index=True)
    service_name = Column(String)
    recommendation_type = Column(String)
    description = Column(String)
    estimated_savings = Column(Float)
    priority = Column(String, default="medium")       # NEW — critical/high/medium
    payback_months = Column(Float, default=1.0)       # NEW — ROI metric
    status = Column(String, default="pending")


class CostHistory(Base):
    __tablename__ = "cost_history"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    service_name = Column(String, index=True)
    region = Column(String, index=True)
    provider = Column(String, default="AWS")          # NEW
    account_id = Column(String, default="")           # NEW
    daily_cost = Column(Float)


class KubernetesUsage(Base):
    __tablename__ = "kubernetes_usage"

    id = Column(Integer, primary_key=True, index=True)
    cluster_name = Column(String, index=True)
    namespace = Column(String, index=True)
    monthly_cost = Column(Float)
    cpu_utilization = Column(Float)
    memory_utilization = Column(Float)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Cost Autopilot Models
# ─────────────────────────────────────────────────────────────────────────────

class AutopilotPolicy(Base):
    __tablename__ = "autopilot_policies"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    enabled = Column(Boolean, default=False)
    max_daily_actions = Column(Integer, default=5)
    allowed_actions = Column(String, default="stop_ec2,delete_ebs,scale_down_vm") # Comma-separated list

    organization = relationship("Organization")


class AutopilotAction(Base):
    __tablename__ = "autopilot_actions"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)
    resource_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    status = Column(String) # success, failed, skipped
    estimated_savings = Column(Float, default=0.0)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization")


class CloudAccount(Base):
    __tablename__ = "cloud_accounts"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    provider = Column(String, index=True)  # "aws", "azure", "gcp"
    credential_type = Column(String)  # "role_arn", "service_principal", "service_account_json", "static_keys"
    credentials_encrypted = Column(String)  # Fernet encrypted JSON blob
    account_alias = Column(String)
    account_id_or_sub = Column(String, nullable=True)  # AWS account ID, Azure sub, GCP project
    region = Column(String, default="us-east-1")
    enabled = Column(Boolean, default=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization")
