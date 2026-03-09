"""
Budget Engine — Production-grade budget monitoring for the FinOps platform.

Responsibilities:
  - Track monthly spending per org/project/provider from CostHistory
  - Compute budget utilization and project end-of-month (EOM) spend
  - Generate severity-rated alerts when spend exceeds configured thresholds
"""
from __future__ import annotations

import calendar
import datetime
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session  # pyre-ignore[21]
from sqlalchemy import func           # pyre-ignore[21]

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _days_in_current_month() -> int:
    today = datetime.date.today()
    return calendar.monthrange(today.year, today.month)[1]


def _current_month_bounds():
    """Return (start_datetime, today_datetime) for the current calendar month."""
    today = datetime.date.today()
    start = datetime.datetime(today.year, today.month, 1)
    end = datetime.datetime.combine(today, datetime.time.max)
    return start, end


def forecast_eom_spend(current_spend: float, day_of_month: int) -> float:
    """
    Linear EOM projection:
        projected = (current_spend / elapsed_days) * total_days_in_month
    Falls back to current_spend when day_of_month == 0 to avoid division by zero.
    """
    if day_of_month <= 0:
        return round(current_spend, 2)
    total_days = _days_in_current_month()
    projected = (current_spend / day_of_month) * total_days
    return round(projected, 2)


def _severity(utilization_pct: float, threshold_pct: float) -> str:
    """Map utilization percentage to a severity label."""
    if utilization_pct >= 1.0:
        return "critical"
    if utilization_pct >= threshold_pct:
        return "warning"
    if utilization_pct >= threshold_pct * 0.8:
        return "info"
    return "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Core engine
# ─────────────────────────────────────────────────────────────────────────────

def get_current_month_spend(
    db: Session,
    org_id: Optional[int] = None,
    provider: Optional[str] = None,
) -> float:
    """
    Sum all CostHistory.daily_cost rows for the current calendar month.
    Optionally filter by provider (AWS / GCP / Azure).
    NOTE: org_id filtering is a future extension — CostHistory does not carry
    org_id yet, so it is accepted for API compatibility but ignored today.
    """
    # Import here to avoid circular imports at module load time
    from models import CostHistory  # pyre-ignore[21]

    start, end = _current_month_bounds()

    query = db.query(func.coalesce(func.sum(CostHistory.daily_cost), 0.0))
    query = query.filter(CostHistory.date >= start, CostHistory.date <= end)
    if provider and provider.lower() != "all":
        query = query.filter(CostHistory.provider == provider)

    result = query.scalar()
    return round(float(result), 2)


def compute_budget_status(budget, db: Session) -> Dict[str, Any]:
    """
    Evaluate a single Budget ORM object against current spending.
    Returns a rich status dict consumed by /api/budget-alerts.
    """
    today = datetime.date.today()
    day_of_month = today.day

    current_spend = get_current_month_spend(
        db,
        org_id=budget.org_id,
        provider=budget.cloud_provider,
    )

    utilization_pct = current_spend / budget.monthly_limit if budget.monthly_limit > 0 else 0.0
    eom_forecast = forecast_eom_spend(current_spend, day_of_month)
    sev = _severity(utilization_pct, budget.alert_threshold_pct)

    return {
        "budget_id": budget.id,
        "budget_name": budget.name,
        "monthly_limit": budget.monthly_limit,
        "current_spend": current_spend,
        "utilization_pct": round(utilization_pct * 100, 1),   # as percentage
        "forecast_eom": eom_forecast,
        "severity": sev,
        "org_id": budget.org_id,
        "project_id": budget.project_id,
        "cloud_provider": budget.cloud_provider,
    }


def check_all_budgets(db: Session) -> List[Dict[str, Any]]:
    """
    Iterate every active budget and return status dicts for those
    whose severity is NOT 'ok' (i.e., approaching or exceeding threshold).
    """
    from models import Budget  # pyre-ignore[21]

    active_budgets = db.query(Budget).filter(Budget.active == True).all()
    alerts: List[Dict[str, Any]] = []

    for budget in active_budgets:
        try:
            status = compute_budget_status(budget, db)
            if status["severity"] != "ok":
                alerts.append(status)
        except Exception as exc:
            logger.error(f"Error checking budget {budget.id}: {exc}")

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 99))
    return alerts


def get_budget_summary(db: Session) -> Dict[str, Any]:
    """
    High-level summary for the dashboard widget:
      total_budget_limit, total_spent, overall_utilization_pct, alerts_count
    """
    from models import Budget  # pyre-ignore[21]

    budgets = db.query(Budget).filter(Budget.active == True).all()
    if not budgets:
        return {
            "total_budget_limit": 0.0,
            "total_spent": 0.0,
            "overall_utilization_pct": 0.0,
            "alerts_count": 0,
        }

    total_limit = sum(b.monthly_limit for b in budgets)
    total_spent = get_current_month_spend(db)
    utilization = (total_spent / total_limit * 100) if total_limit > 0 else 0.0
    alerts = check_all_budgets(db)

    return {
        "total_budget_limit": round(total_limit, 2),
        "total_spent": total_spent,
        "overall_utilization_pct": round(utilization, 1),
        "alerts_count": len(alerts),
    }
