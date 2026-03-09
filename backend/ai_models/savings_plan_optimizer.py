"""
Savings Plan Optimizer — Commitment purchase recommendation engine.

Analyses monthly spend patterns and recommends the optimal commitment
(Savings Plans, Reserved Instances, Committed Use Discounts) per cloud provider.

Includes break-even analysis so engineers can see exactly when a commitment pays off.
"""
from __future__ import annotations
import math
from typing import List, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# Discount rate tables (on-demand → committed, approximate)
# ─────────────────────────────────────────────────────────────────────────────

AWS_SAVINGS_PLANS = [
    {
        "plan_name": "Compute Savings Plan — 1yr No Upfront",
        "commitment_months": 12,
        "discount_pct": 0.25,   # ~25% off on-demand
        "upfront_cost_ratio": 0.0,
        "provider": "AWS",
        "commitment_type": "savings_plan",
    },
    {
        "plan_name": "Compute Savings Plan — 1yr All Upfront",
        "commitment_months": 12,
        "discount_pct": 0.35,
        "upfront_cost_ratio": 12.0,  # Pay 12 months upfront
        "provider": "AWS",
        "commitment_type": "savings_plan",
    },
    {
        "plan_name": "EC2 Reserved Instance — 1yr No Upfront",
        "commitment_months": 12,
        "discount_pct": 0.32,
        "upfront_cost_ratio": 0.0,
        "provider": "AWS",
        "commitment_type": "reserved_instance",
    },
    {
        "plan_name": "EC2 Reserved Instance — 3yr All Upfront",
        "commitment_months": 36,
        "discount_pct": 0.55,
        "upfront_cost_ratio": 36.0,
        "provider": "AWS",
        "commitment_type": "reserved_instance",
    },
]

GCP_COMMITTED_USE = [
    {
        "plan_name": "GCP Committed Use Discount — 1yr",
        "commitment_months": 12,
        "discount_pct": 0.37,
        "upfront_cost_ratio": 0.0,
        "provider": "GCP",
        "commitment_type": "committed_use",
    },
    {
        "plan_name": "GCP Committed Use Discount — 3yr",
        "commitment_months": 36,
        "discount_pct": 0.55,
        "upfront_cost_ratio": 0.0,
        "provider": "GCP",
        "commitment_type": "committed_use",
    },
]

AZURE_RESERVED = [
    {
        "plan_name": "Azure Reserved VM — 1yr",
        "commitment_months": 12,
        "discount_pct": 0.35,
        "upfront_cost_ratio": 0.0,
        "provider": "Azure",
        "commitment_type": "reserved_vm",
    },
    {
        "plan_name": "Azure Reserved VM — 3yr",
        "commitment_months": 36,
        "discount_pct": 0.50,
        "upfront_cost_ratio": 0.0,
        "provider": "Azure",
        "commitment_type": "reserved_vm",
    },
    {
        "plan_name": "Azure Savings Plan — 1yr",
        "commitment_months": 12,
        "discount_pct": 0.15,
        "upfront_cost_ratio": 0.0,
        "provider": "Azure",
        "commitment_type": "savings_plan",
    },
]

ALL_PLANS: List[Dict[str, Any]] = AWS_SAVINGS_PLANS + GCP_COMMITTED_USE + AZURE_RESERVED


# ─────────────────────────────────────────────────────────────────────────────
# Break-even analysis
# ─────────────────────────────────────────────────────────────────────────────

def _break_even_months(
    monthly_spend: float,
    discount_pct: float,
    upfront_ratio: float,
) -> float:
    """
    How many months until the commitment savings pay back the upfront cost?
    If no upfront cost, break-even is immediate (return 0).
    """
    monthly_savings = monthly_spend * discount_pct
    if monthly_savings <= 0:
        return 999.0
    upfront = monthly_spend * upfront_ratio
    if upfront <= 0:
        return 0.0
    return round(upfront / monthly_savings, 1)


def _avg_monthly_spend(history_data: List[Dict[str, Any]]) -> float:
    """Average daily cost scaled to monthly (×30)."""
    if not history_data:
        return 0.0
    avg_daily = sum(float(h.get("cost", 0.0)) for h in history_data) / len(history_data)
    return round(avg_daily * 30, 2)


def _spend_stability(history_data: List[Dict[str, Any]]) -> float:
    """
    Returns a stability score 0–1 where 1 = very stable spend (ideal for commitments).
    Uses coefficient of variation: lower CV = more stable.
    """
    if len(history_data) < 7:
        return 0.5
    costs = [float(h.get("cost", 0.0)) for h in history_data]
    mean = sum(costs) / len(costs)
    if mean == 0:
        return 0.0
    variance = sum((c - mean) ** 2 for c in costs) / len(costs)
    cv = math.sqrt(variance) / mean   # Coefficient of variation
    return round(max(0.0, 1.0 - cv), 3)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def recommend_savings_plans(
    history_data: List[Dict[str, Any]],
    provider_filter: str = "all",
) -> Dict[str, Any]:
    """
    Analyse historical cost data and recommend commitment purchase plans.

    Args:
        history_data:    list of {date, cost} from /api/cost-history
        provider_filter: "all" | "AWS" | "GCP" | "Azure"

    Returns:
        {
            "monthly_spend": float,
            "spend_stability": float,
            "recommendations": [...],
            "summary": {...}
        }
    """
    monthly_spend = _avg_monthly_spend(history_data)
    stability = _spend_stability(history_data)

    # Pick plans for selected provider(s)
    plans = [
        p for p in ALL_PLANS
        if provider_filter.lower() == "all" or p["provider"] == provider_filter
    ]

    recs: List[Dict[str, Any]] = []
    for plan in plans:
        disc = plan["discount_pct"]
        monthly_savings = round(monthly_spend * disc, 2)
        annual_savings = round(monthly_savings * 12, 2)
        total_commitment_cost = round(monthly_spend * (1 - disc) * plan["commitment_months"], 2)
        upfront = round(monthly_spend * plan["upfront_cost_ratio"], 2)
        breakeven = _break_even_months(monthly_spend, disc, plan["upfront_cost_ratio"])

        # Confidence: high stability + large savings → recommend more strongly
        confidence = round(min(stability * 60 + (disc * 100) * 0.4, 100.0), 1)

        rec: Dict[str, Any] = {
            "plan_name": plan["plan_name"],
            "provider": plan["provider"],
            "commitment_type": plan["commitment_type"],
            "commitment_months": plan["commitment_months"],
            "current_monthly_spend": monthly_spend,
            "discount_pct": round(disc * 100, 1),       # as percentage
            "estimated_monthly_savings": monthly_savings,
            "estimated_annual_savings": annual_savings,
            "total_commitment_cost": total_commitment_cost,
            "upfront_payment": upfront,
            "breakeven_months": breakeven,
            "spend_stability_score": round(stability * 100, 1),  # as percentage
            "confidence_score": confidence,
            "recommended": confidence >= 55.0 and monthly_savings >= 50.0,
        }
        recs.append(rec)

    # Sort: recommended first, then by annual savings desc
    recs.sort(key=lambda r: (not r["recommended"], -r["estimated_annual_savings"]))

    top_rec = recs[0] if recs else {}
    return {
        "monthly_spend": monthly_spend,
        "spend_stability_score": round(stability * 100, 1),
        "recommendations": recs,
        "summary": {
            "best_plan": top_rec.get("plan_name", "N/A"),
            "best_annual_savings": top_rec.get("estimated_annual_savings", 0.0),
            "best_discount_pct": top_rec.get("discount_pct", 0.0),
            "recommendation_count": len([r for r in recs if r["recommended"]]),
        },
    }
