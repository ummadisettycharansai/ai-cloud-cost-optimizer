import logging
from fastapi import FastAPI, Depends, HTTPException, status, Query  # pyre-ignore[21]
from fastapi.middleware.cors import CORSMiddleware  # pyre-ignore[21]
from fastapi.responses import Response  # pyre-ignore[21]
from fastapi.security import OAuth2PasswordRequestForm  # pyre-ignore[21]
from sqlalchemy.orm import Session  # pyre-ignore[21]
from typing import Optional, List

logger = logging.getLogger(__name__)
import models  # pyre-ignore[21]
import schemas # pyre-ignore[21]
import crud    # pyre-ignore[21]
from models import Base, CloudResource, CostHistory  # pyre-ignore[21]
from schemas import (
    OrganizationCreate, OrganizationOut, ProjectCreate, ProjectOut,
    BudgetCreate, BudgetOut, AutopilotPolicyOut, AutopilotActionOut,
    AutopilotRunResult, CloudAccountOut, CloudAccountCreateAWS,
    CloudAccountCreateAzure, CloudAccountCreateGCP
)
from crud import (  # pyre-ignore[21]
    get_autopilot_actions, create_organization, get_organizations,
    get_organization, create_project, get_projects, create_budget,
    get_budgets, get_autopilot_policy, enable_autopilot, disable_autopilot,
    get_cloud_accounts, create_cloud_account, delete_cloud_account,
    get_cloud_account_by_id, update_cloud_account_sync_time
)
from database import engine, get_db  # pyre-ignore[21]

from services.aws_service import AWSService  # pyre-ignore[21]
from services.gcp_service import GCPService  # pyre-ignore[21]
from services.azure_service import AzureService  # pyre-ignore[21]
from services.kubernetes_service import KubernetesService  # pyre-ignore[21]

from ai_models.anomaly_detector import CostAnomalyDetector  # pyre-ignore[21]
from ai_models.forecaster import CostForecaster  # pyre-ignore[21]
from ai_models.cost_optimizer import CloudCostOptimizer  # pyre-ignore[21]
from optimizer.recommendation_engine import RecommendationEngine  # pyre-ignore[21]
from alerts.alert_engine import AlertEngine  # pyre-ignore[21]
from cloud_integrations.credential_manager import get_credential_manager  # NEW: credential management
from budgets.budget_engine import (  # pyre-ignore[21]
    check_all_budgets, compute_budget_status, get_budget_summary,
)

from auth.auth_handler import authenticate_user, create_access_token  # pyre-ignore[21]
from auth.rbac import RequireRole  # NEW: Enforce RBAC
from observability.metrics import (  # pyre-ignore[21]
    get_metrics_response,
    setup_tracing,
    api_requests_total,
    anomalies_detected_total,
    forecast_requests_total,
    alerts_sent_total,
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Cloud Cost Optimizer API",
    description="Production-grade FinOps SaaS platform: multi-tenant, multi-cloud cost monitoring, AI anomaly detection, forecasting, optimization, and budget management.",
    version="3.0.0",
)

# Initialize OpenTelemetry tracing
setup_tracing("ai-cloud-cost-optimizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Service / AI singletons ─────────────────────────────────────────────────
aws_service = AWSService()
gcp_service = GCPService()
azure_service = AzureService()
k8s_service = KubernetesService()

anomaly_detector = CostAnomalyDetector()
forecaster = CostForecaster()
optimizer = RecommendationEngine()
cost_optimizer = CloudCostOptimizer()
alert_engine = AlertEngine()


# ── Internal helpers ─────────────────────────────────────────────────────────

def _get_all_resources():
    return (
        aws_service.fetch_current_resources() +
        gcp_service.fetch_current_resources() +
        azure_service.fetch_current_resources()
    )


def _get_all_history(days=60):
    aws_hist = aws_service.fetch_historical_costs(days)
    gcp_hist = gcp_service.fetch_historical_costs(days)
    azure_hist = azure_service.fetch_historical_costs(days)

    combined = {}
    for h_list in [aws_hist, gcp_hist, azure_hist]:
        for entry in h_list:
            d = entry['date']
            combined[d] = combined.get(d, 0.0) + entry['cost']

    return [{"date": k, "cost": round(float(v), 2)} for k, v in combined.items()]  # pyre-ignore[6]


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate with username + password and receive a JWT access token.
    Demo credentials: admin/secret  |  finance/secret  |  engineer/secret
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


# ══════════════════════════════════════════════════════════════════════════════
# OBSERVABILITY
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/metrics")
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    data, content_type = get_metrics_response()
    return Response(content=data, media_type=content_type)


@app.get("/health")
def health_check():
    """Liveness probe for Kubernetes / Docker healthcheck."""
    return {"status": "healthy", "version": "3.0.0"}


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "AI Cloud Cost Optimizer API — FinOps SaaS Production Edition",
        "version": "3.0.0",
        "docs": "/docs",
    }


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/dashboard/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    resources = _get_all_resources()
    total_cost = sum(r.get('monthly_cost', 0) for r in resources)
    active_count = len([r for r in resources if r.get('status') == 'running'])
    budget_summary = get_budget_summary(db)
    
    # Calculate Autopilot Savings
    actions = get_autopilot_actions(db, org_id=1, limit=1000)
    autopilot_savings = sum(a.estimated_savings for a in actions if a.status == "success")

    return {
        "total_monthly_cost": round(float(total_cost), 2),  # pyre-ignore[6]
        "cost_change_percentage": 5.2,
        "active_resources": active_count,
        "detected_anomalies_count": 0,
        "budget_summary": budget_summary,
        "autopilot_savings": autopilot_savings,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CLOUD RESOURCES & COSTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/resources")
def get_resources():
    return _get_all_resources()


@app.get("/api/cost-by-service")
def get_cost_by_service():
    resources = _get_all_resources()
    service_costs = {}
    for r in resources:
        svc = r.get("service_name", "Unknown")
        cost = r.get("monthly_cost", 0.0)
        svc_clean = (
            svc.replace("Amazon ", "").replace("AWS ", "")
               .replace("Google ", "").replace("Azure ", "")
        )
        service_costs[svc_clean] = service_costs.get(svc_clean, 0.0) + cost
    return {svc: round(float(c), 2) for svc, c in service_costs.items()}  # pyre-ignore[6]


@app.get("/api/cost-by-region")
def get_cost_by_region():
    resources = _get_all_resources()
    region_costs = {}
    for r in resources:
        reg = r.get("region", "Global")
        cost = r.get("monthly_cost", 0.0)
        region_costs[reg] = region_costs.get(reg, 0.0) + cost
    return {k: round(float(v), 2) for k, v in region_costs.items()}  # pyre-ignore[6]


@app.get("/api/kubernetes-cost")
def get_kubernetes_cost():
    return k8s_service.fetch_namespace_costs()


@app.get("/api/cost-history")
def get_cost_history():
    return _get_all_history(days=30)


@app.get("/api/demo-costs")
def get_demo_costs():
    """Returns 30 days of realistic demo cloud billing data."""
    from demo.demo_cost_data import generate_demo_costs  # pyre-ignore[21]
    return generate_demo_costs(days=30)


# ══════════════════════════════════════════════════════════════════════════════
# AI — Anomalies, Forecast, Recommendations
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/anomalies")
def get_anomalies():
    history = _get_all_history(days=60)
    anomalies_data = anomaly_detector.detect_anomalies(history)
    return [a for a in anomalies_data if a.get('is_anomaly')]


@app.get("/api/alerts")
def get_alerts():
    anomalies = get_anomalies()
    return alert_engine.process_anomalies(anomalies)


@app.get("/api/forecast")
def get_forecast(days: int = Query(default=30, ge=7, le=90)):
    history = _get_all_history(days=60)
    return forecaster.forecast_costs(history, forecast_days=days)


@app.get("/api/recommendations")
def get_recommendations():
    active_resources = _get_all_resources()
    return optimizer.generate_recommendations(active_resources)


@app.get("/api/savings-opportunities")
def get_savings_opportunities():
    recs = get_recommendations()
    total_savings = sum(r.get('estimated_savings', 0) for r in recs)
    return {
        "potential_savings": round(float(total_savings), 2),  # pyre-ignore[6]
        "recommendations": recs,
    }


@app.get("/api/cost-efficiency")
def get_cost_efficiency():
    """Returns all resources scored by cost efficiency (0–100)."""
    resources = _get_all_resources()
    scored = cost_optimizer.score_resources(resources)
    top_waste = cost_optimizer.get_top_waste_candidates(scored, top_n=10)
    return {
        "all_resources": scored,
        "top_waste_candidates": top_waste,
        "summary": cost_optimizer.efficiency_summary(scored),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-TENANT — Organizations
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/organizations", response_model=OrganizationOut, status_code=201, dependencies=[Depends(RequireRole(["admin"]))])
def create_org(org: OrganizationCreate, db: Session = Depends(get_db)):
    """Create a new organization (tenant)."""
    return create_organization(db, org)


@app.get("/api/organizations", response_model=List[OrganizationOut])
def list_orgs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all organizations."""
    return get_organizations(db, skip=skip, limit=limit)


@app.get("/api/organizations/{org_id}", response_model=OrganizationOut)
def get_org(org_id: int, db: Session = Depends(get_db)):
    """Get a single organization by ID."""
    org = get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-TENANT — Projects
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/projects", response_model=ProjectOut, status_code=201, dependencies=[Depends(RequireRole(["admin"]))])
def create_proj(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project under an organization."""
    return create_project(db, project)


@app.get("/api/projects", response_model=List[ProjectOut])
def list_projects(
    org_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all projects, optionally filtered by org_id."""
    return get_projects(db, org_id=org_id, skip=skip, limit=limit)


# ══════════════════════════════════════════════════════════════════════════════
# BUDGET MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/budgets", response_model=BudgetOut, status_code=201, dependencies=[Depends(RequireRole(["admin", "finance"]))])
def create_budget_endpoint(budget: BudgetCreate, db: Session = Depends(get_db)):
    """Create a new budget for an org/project."""
    return create_budget(db, budget)


@app.get("/api/budgets", response_model=List[BudgetOut])
def list_budgets(
    org_id: Optional[int] = None,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all budgets, with optional org/project filters."""
    return get_budgets(db, org_id=org_id, project_id=project_id, skip=skip, limit=limit)


@app.get("/api/budget-alerts")
def get_budget_alerts(db: Session = Depends(get_db)):
    """
    Run the budget engine across all active budgets and return
    those whose spending is approaching or exceeding the threshold.
    """
    return check_all_budgets(db)


@app.get("/api/budget-summary")
def get_budget_summary_endpoint(db: Session = Depends(get_db)):
    """High-level budget utilization summary for the dashboard widget."""
    from budgets.budget_engine import get_budget_summary as _get_summary  # pyre-ignore[21]
    return _get_summary(db)


# ══════════════════════════════════════════════════════════════════════════════
# AI OPTIMIZATION ENGINE — Right-Sizing / Savings Plans / Anomaly Explain
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/rightsizing")
def get_rightsizing(db: Session = Depends(get_db)):
    """
    ML-based right-sizing recommendations for all compute resources.
    Returns resources that are over-provisioned with a recommended instance type,
    confidence score, estimated savings, and cross-cloud equivalence.
    """
    from ai_models.rightsizing_engine import generate_rightsizing_recommendations  # pyre-ignore[21]
    try:
        # Gather resources from all providers
        all_resources = []
        aws = AWSService()
        gcp = GCPService()
        azure = AzureService()
        for r in aws.fetch_current_resources():
            r["provider"] = "AWS"
            all_resources.append(r)
        for r in gcp.fetch_current_resources():
            r["provider"] = "GCP"
            all_resources.append(r)
        for r in azure.fetch_current_resources():
            r["provider"] = "Azure"
            all_resources.append(r)

        return generate_rightsizing_recommendations(all_resources)
    except Exception as e:
        logger.error(f"Right-sizing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/savings-plans")
def get_savings_plans(
    provider: str = "all",
    db: Session = Depends(get_db),
):
    """
    Analyse historical spend and recommend commitment purchases
    (Savings Plans, Reserved Instances, Committed Use Discounts).
    Includes estimated annual savings, break-even analysis, and confidence scores.
    """
    from ai_models.savings_plan_optimizer import recommend_savings_plans  # pyre-ignore[21]
    from models import CostHistory  # pyre-ignore[21]
    try:
        rows = db.query(CostHistory).order_by(CostHistory.date).all()
        history = [{"date": str(r.date.date()), "cost": r.daily_cost} for r in rows]
        return recommend_savings_plans(history, provider_filter=provider)
    except Exception as e:
        logger.error(f"Savings plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anomaly-explain")
def explain_anomalies_endpoint(db: Session = Depends(get_db)):
    """
    Run anomaly detection on the full history and return root-cause explanations
    for every anomalous data point including fix suggestions.
    """
    from ai_models.anomaly_explainer import explain_anomalies  # pyre-ignore[21]
    from models import CostHistory  # pyre-ignore[21]
    try:
        rows = db.query(CostHistory).order_by(CostHistory.date).all()
        history = [{"date": str(r.date.date()), "cost": r.daily_cost} for r in rows]
        if len(history) < 5:
            return []
        detector = CostAnomalyDetector()
        anomaly_data = detector.detect_anomalies(history)
        return explain_anomalies(anomaly_data, full_history=history)
    except Exception as e:
        logger.error(f"Anomaly explain error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anomaly-explain/{date_str}")
def explain_single_anomaly(date_str: str, db: Session = Depends(get_db)):
    """Root-cause explanation for a specific anomaly date (YYYY-MM-DD)."""
    from ai_models.anomaly_explainer import explain_single  # pyre-ignore[21]
    from models import CostHistory  # pyre-ignore[21]
    try:
        rows = db.query(CostHistory).order_by(CostHistory.date).all()
        history = [{"date": str(r.date.date()), "cost": r.daily_cost} for r in rows]
        detector = CostAnomalyDetector()
        anomaly_data = detector.detect_anomalies(history)
        result = explain_single(date_str, anomaly_data)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No anomaly found for date {date_str}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single anomaly explain error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3: AI COST AUTOPILOT (AUTO-REMEDIATION)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/autopilot/status", response_model=AutopilotPolicyOut)
def get_autopilot_status(org_id: int = 1, db: Session = Depends(get_db)):
    """Fetch the current Autopilot safety policy for the organization."""
    return get_autopilot_policy(db, org_id)


@app.post("/api/autopilot/enable", response_model=AutopilotPolicyOut)
def api_enable_autopilot(
    org_id: int = 1,
    db: Session = Depends(get_db),
    user_role: str = Depends(RequireRole(["admin"])),
):
    """Enable the Cost Autopilot for the given organization (Admin only)."""
    return enable_autopilot(db, org_id)


@app.post("/api/autopilot/disable", response_model=AutopilotPolicyOut)
def api_disable_autopilot(
    org_id: int = 1,
    db: Session = Depends(get_db),
    user_role: str = Depends(RequireRole(["admin"])),
):
    """Disable the Cost Autopilot for the given organization (Admin only)."""
    return disable_autopilot(db, org_id)


@app.get("/api/autopilot/actions", response_model=List[AutopilotActionOut])
def api_get_autopilot_actions(org_id: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    """Fetch recently executed Autopilot remediation actions."""
    return get_autopilot_actions(db, org_id, limit)


@app.post("/api/autopilot/run", response_model=AutopilotRunResult)
def run_autopilot_manually(org_id: int = 1, db: Session = Depends(get_db)):
    """
    Manually trigger the Autopilot to evaluate active resources,
    generate recommendations, and execute allowed remediation actions.
    """
    from remediation.remediation_engine import RemediationEngine # pyre-ignore[21]
    
    # 1. Fetch active resources
    resources = db.query(CloudResource).all()
    active = [
        {
            "resource_id": r.resource_id,
            "service_name": r.service_name,
            "provider": r.provider,
            "status": r.status,
            "cpu_utilization": r.cpu_utilization,
            "monthly_cost": r.monthly_cost
        }
        for r in resources
    ]
    
    # 2. Generate Recommendations
    recommender = RecommendationEngine()
    recs = recommender.generate_recommendations(active)

    if not recs:
        return {
            "message": "No actionable recommendations found.",
            "actions_executed": 0,
            "actions_skipped": 0,
            "total_savings_estimated": 0.0
        }

    # 3. Process via Autopilot Engine
    engine = RemediationEngine(db)
    executed_count: int = 0
    skipped_count: int = 0
    savings_total: float = 0.0
    for rec in recs:
        result = engine.process_recommendation(org_id, rec)
        if result and result.status == "success":
            executed_count = int(executed_count) + 1  # pyre-ignore[6, 58]
            savings_total = float(savings_total) + float(result.estimated_savings or 0.0)  # pyre-ignore[6, 58]
        else:
            skipped_count = int(skipped_count) + 1  # pyre-ignore[6, 58]
        
    return {
        "message": f"Evaluated {len(recs)} recommendations.",
        "actions_executed": executed_count,
        "actions_skipped": skipped_count,
        "total_savings_estimated": savings_total
    }

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4: CLOUD ACCOUNT CONNECTIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/cloud/accounts", response_model=List[CloudAccountOut])
def api_get_cloud_accounts(org_id: int = 1, db: Session = Depends(get_db)):
    """List all connected cloud accounts for the organization."""
    return get_cloud_accounts(db, org_id)

@app.post("/api/connect/aws", response_model=CloudAccountOut, status_code=201)
def connect_aws_account(
    account_in: CloudAccountCreateAWS,
    db: Session = Depends(get_db),
    user_role: str = Depends(RequireRole(["admin"])),
):
    """Connect an AWS account securely."""
    org_id = account_in.org_id
    mgr = get_credential_manager()
    creds = {}
    if account_in.role_arn:
        creds["role_arn"] = account_in.role_arn
        cred_type = "role_arn"
    elif account_in.access_key and account_in.secret_key:
        creds["access_key"] = account_in.access_key
        creds["secret_key"] = account_in.secret_key
        cred_type = "static_keys"
    else:
        cred_type = "default_chain"

    encrypted_blob = mgr.encrypt(creds)
    return create_cloud_account(
        db=db,
        org_id=org_id,
        provider="aws",
        credential_type=cred_type,
        account_alias=account_in.account_alias,
        credentials_encrypted=encrypted_blob,
        region=account_in.region,
        account_id_or_sub=None,  # Typically fetched on first sync
    )

@app.post("/api/connect/azure", response_model=CloudAccountOut, status_code=201)
def connect_azure_account(
    account_in: CloudAccountCreateAzure,
    db: Session = Depends(get_db),
    user_role: str = Depends(RequireRole(["admin"])),
):
    """Connect an Azure subscription securely using a Service Principal."""
    org_id = account_in.org_id
    mgr = get_credential_manager()
    creds = {
        "tenant_id": account_in.tenant_id,
        "client_id": account_in.client_id,
        "client_secret": account_in.client_secret,
        "subscription_id": account_in.subscription_id,
    }
    encrypted_blob = mgr.encrypt(creds)
    return create_cloud_account(
        db=db,
        org_id=org_id,
        provider="azure",
        credential_type="service_principal",
        account_alias=account_in.account_alias,
        credentials_encrypted=encrypted_blob,
        region=account_in.region,
        account_id_or_sub=account_in.subscription_id,
    )

@app.post("/api/connect/gcp", response_model=CloudAccountOut, status_code=201)
def connect_gcp_account(
    account_in: CloudAccountCreateGCP,
    db: Session = Depends(get_db),
    user_role: str = Depends(RequireRole(["admin"])),
):
    """Connect a GCP project securely using a Service Account JSON."""
    org_id = account_in.org_id
    mgr = get_credential_manager()
    creds = {
        "project_id": account_in.project_id,
        "service_account_json": account_in.service_account_json,
    }
    encrypted_blob = mgr.encrypt(creds)
    return create_cloud_account(
        db=db,
        org_id=org_id,
        provider="gcp",
        credential_type="service_account_json",
        account_alias=account_in.account_alias,
        credentials_encrypted=encrypted_blob,
        region=account_in.region,
        account_id_or_sub=account_in.project_id,
    )

@app.delete("/api/cloud/accounts/{account_id}", status_code=204)
def api_delete_cloud_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_role: str = Depends(RequireRole(["admin"])),
):
    """Remove a connected cloud account."""
    success = delete_cloud_account(db, account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cloud account not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/api/cloud/accounts/{account_id}/sync")
def api_sync_cloud_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_role: str = Depends(RequireRole(["admin"])),
):
    """Trigger an immediate cost + resource sync for the given account."""
    account = get_cloud_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found.")
    
    # In a real app we'd dispatch a Celery task here:
    # sync_cloud_account_now.delay(account_id)
    
    # Mark synced locally for simulation
    update_cloud_account_sync_time(db, account_id)
    return {"message": f"Sync triggered successfully for {account.provider} account {account.account_alias}."}


