from sqlalchemy.orm import Session  # pyre-ignore[21]
from typing import Optional, List

import models  # pyre-ignore[21]
import schemas  # pyre-ignore[21]
from models import (  # pyre-ignore[21]
    CloudResource, CostAnomaly, OptimizationRecommendation,
    Organization, Project, Budget,
    AutopilotPolicy, AutopilotAction, CloudAccount
)
from schemas import (  # pyre-ignore[21]
    CloudResourceCreate,
    OrganizationCreate, ProjectCreate, BudgetCreate,
    AutopilotPolicyCreate
)


# ─────────────────────────────────────────────────────────────────────────────
# Original resource CRUD
# ─────────────────────────────────────────────────────────────────────────────

def get_resources(db: Session, skip: int = 0, limit: int = 100):
    return db.query(CloudResource).offset(skip).limit(limit).all()


def get_anomalies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(CostAnomaly).offset(skip).limit(limit).all()


def get_recommendations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(OptimizationRecommendation).offset(skip).limit(limit).all()


def create_resource(db: Session, resource: CloudResourceCreate):
    db_resource = CloudResource(**resource.model_dump())
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource


# ─────────────────────────────────────────────────────────────────────────────
# Organization CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_organization(db: Session, org: OrganizationCreate):
    db_org = Organization(**org.model_dump())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org


def get_organizations(db: Session, skip: int = 0, limit: int = 100) -> List[Organization]:
    return db.query(Organization).offset(skip).limit(limit).all()


def get_organization(db: Session, org_id: int) -> Optional[Organization]:
    return db.query(Organization).filter(Organization.id == org_id).first()


# ─────────────────────────────────────────────────────────────────────────────
# Project CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_project(db: Session, project: ProjectCreate):
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_projects(
    db: Session,
    org_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Project]:
    q = db.query(Project)
    if org_id is not None:
        q = q.filter(Project.org_id == org_id)
    return q.offset(skip).limit(limit).all()


# ─────────────────────────────────────────────────────────────────────────────
# Budget CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_budget(db: Session, budget: BudgetCreate):
    db_budget = Budget(**budget.model_dump())
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


def get_budgets(
    db: Session,
    org_id: Optional[int] = None,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Budget]:
    q = db.query(Budget)
    if org_id is not None:
        q = q.filter(Budget.org_id == org_id)
    if project_id is not None:
        q = q.filter(Budget.project_id == project_id)
    return q.offset(skip).limit(limit).all()


def get_budget(db: Session, budget_id: int) -> Optional[Budget]:
    return db.query(Budget).filter(Budget.id == budget_id).first()


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Cost Autopilot CRUD
# ─────────────────────────────────────────────────────────────────────────────

def get_autopilot_policy(db: Session, org_id: int) -> Optional[AutopilotPolicy]:
    """Get the org's autopilot policy, creating a disabled default if missing."""
    policy = db.query(AutopilotPolicy).filter(AutopilotPolicy.org_id == org_id).first()
    if not policy:
        policy = AutopilotPolicy(org_id=org_id, enabled=False, max_daily_actions=5)
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return policy

def enable_autopilot(db: Session, org_id: int) -> AutopilotPolicy:
    policy = get_autopilot_policy(db, org_id)
    if policy:
        policy.enabled = True
        db.commit()
        db.refresh(policy)
    return policy

def disable_autopilot(db: Session, org_id: int) -> AutopilotPolicy:
    policy = get_autopilot_policy(db, org_id)
    if policy:
        policy.enabled = False
        db.commit()
        db.refresh(policy)
    return policy

def log_autopilot_action(db: Session, action_data: dict) -> AutopilotAction:
    action = AutopilotAction(**action_data)
    db.add(action)
    db.commit()
    db.refresh(action)
    return action

def get_autopilot_actions(db: Session, org_id: int, limit: int = 50) -> List[AutopilotAction]:
    return (
        db.query(AutopilotAction)
        .filter(AutopilotAction.org_id == org_id)
        .order_by(AutopilotAction.executed_at.desc())
        .limit(limit)
        .all()
    )

def get_daily_action_count(db: Session, org_id: int) -> int:
    import datetime
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(AutopilotAction)
        .filter(AutopilotAction.org_id == org_id)
        .filter(AutopilotAction.executed_at >= today_start)
        .filter(AutopilotAction.status.in_(["success", "pending"]))
        .count()
    )

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Cloud Integration CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_cloud_account(db: Session, org_id: int, provider: str, credential_type: str, account_alias: str, credentials_encrypted: str, region: str = "us-east-1", account_id_or_sub: Optional[str] = None) -> CloudAccount:
    """Create a new connected cloud account for an organization."""
    account = CloudAccount(
        org_id=org_id,
        provider=provider,
        credential_type=credential_type,
        account_alias=account_alias,
        credentials_encrypted=credentials_encrypted,
        region=region,
        account_id_or_sub=account_id_or_sub,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

def get_cloud_accounts(db: Session, org_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[CloudAccount]:
    q = db.query(CloudAccount)
    if org_id is not None:
        q = q.filter(CloudAccount.org_id == org_id)
    return q.offset(skip).limit(limit).all()

def get_cloud_account_by_id(db: Session, account_id: int) -> Optional[CloudAccount]:
    return db.query(CloudAccount).filter(CloudAccount.id == account_id).first()

def get_cloud_account_by_org_provider(db: Session, org_id: int, provider: str) -> Optional[CloudAccount]:
    """Get the primary cloud account for an org and provider."""
    # Assuming one account per provider per org for simplicity in this system
    return db.query(CloudAccount).filter(CloudAccount.org_id == org_id, CloudAccount.provider == provider, CloudAccount.enabled == True).first()

def delete_cloud_account(db: Session, account_id: int) -> bool:
    account = get_cloud_account_by_id(db, account_id)
    if account:
        db.delete(account)
        db.commit()
        return True
    return False

def update_cloud_account_sync_time(db: Session, account_id: int) -> Optional[CloudAccount]:
    import datetime
    account = get_cloud_account_by_id(db, account_id)
    if account:
        account.last_synced_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(account)
    return account