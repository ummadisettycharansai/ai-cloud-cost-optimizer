from pydantic import BaseModel, Field  # pyre-ignore[21]
from typing import Optional, List
import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Organization Schemas
# ─────────────────────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    plan: Optional[str] = "free"


class OrganizationOut(BaseModel):
    id: int
    name: str
    slug: str
    plan: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# Project Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    org_id: int
    name: str
    cloud_provider: Optional[str] = "AWS"
    description: Optional[str] = ""
    tags: Optional[str] = ""


class ProjectOut(BaseModel):
    id: int
    org_id: int
    name: str
    cloud_provider: str
    description: str
    tags: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# Budget Schemas
# ─────────────────────────────────────────────────────────────────────────────

class BudgetCreate(BaseModel):
    org_id: int
    project_id: Optional[int] = None
    name: str
    monthly_limit: float
    alert_threshold_pct: Optional[float] = 0.80
    cloud_provider: Optional[str] = "All"


class BudgetOut(BaseModel):
    id: int
    org_id: int
    project_id: Optional[int]
    name: str
    monthly_limit: float
    alert_threshold_pct: float
    cloud_provider: str
    active: bool
    period_start: datetime.datetime

    class Config:
        from_attributes = True


class BudgetAlertOut(BaseModel):
    budget_id: int
    budget_name: str
    monthly_limit: float
    current_spend: float
    utilization_pct: float
    forecast_eom: float
    severity: str   # warning | critical


# ─────────────────────────────────────────────────────────────────────────────
# Original Schemas (preserved)
# ─────────────────────────────────────────────────────────────────────────────

class CloudResourceBase(BaseModel):
    service_name: str
    resource_id: str
    region: str
    status: str
    monthly_cost: float
    cpu_utilization: float


class CloudResourceCreate(CloudResourceBase):
    pass


class CloudResourceResponse(CloudResourceBase):
    id: int

    class Config:
        from_attributes = True


class CostAnomalyBase(BaseModel):
    service_name: str
    expected_cost: float
    actual_cost: float
    severity: str


class CostAnomalyCreate(CostAnomalyBase):
    pass


class CostAnomalyResponse(CostAnomalyBase):
    id: int
    anomaly_date: datetime.datetime

    class Config:
        from_attributes = True


class RecommendationBase(BaseModel):
    resource_id: str
    service_name: str
    recommendation_type: str
    description: str
    estimated_savings: float


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationResponse(RecommendationBase):
    id: int
    status: str

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Cost Autopilot Schemas
# ─────────────────────────────────────────────────────────────────────────────

class AutopilotPolicyBase(BaseModel):
    enabled: bool
    max_daily_actions: int
    allowed_actions: str

class AutopilotPolicyCreate(AutopilotPolicyBase):
    org_id: int

class AutopilotPolicyOut(AutopilotPolicyBase):
    id: int
    org_id: int

    class Config:
        from_attributes = True

class AutopilotActionOut(BaseModel):
    id: int
    org_id: int
    provider: str
    resource_id: str
    action: str
    status: str
    estimated_savings: float
    executed_at: datetime.datetime

    class Config:
        from_attributes = True

class AutopilotRunResult(BaseModel):
    message: str
    actions_executed: int
    actions_skipped: int
    total_savings_estimated: float


class CloudAccountCreateBase(BaseModel):
    org_id: int
    provider: str
    account_alias: str
    region: str = "us-east-1"
    
class CloudAccountCreateAWS(CloudAccountCreateBase):
    provider: str = Field("aws", pattern="^aws$")
    role_arn: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None

class CloudAccountCreateAzure(CloudAccountCreateBase):
    provider: str = Field("azure", pattern="^azure$")
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str

class CloudAccountCreateGCP(CloudAccountCreateBase):
    provider: str = Field("gcp", pattern="^gcp$")
    project_id: str
    service_account_json: str

class CloudAccountOut(BaseModel):
    id: int
    org_id: int
    provider: str
    credential_type: str
    account_alias: str
    account_id_or_sub: Optional[str] = None
    region: str
    enabled: bool
    last_synced_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True
