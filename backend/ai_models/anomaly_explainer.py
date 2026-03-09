"""
Anomaly Explainer — Root-cause analysis for detected cost anomalies.

For each anomaly detected by the IsolationForest model, this module
attempts to classify the most likely root cause and suggest actionable fixes.

Root cause categories:
  - service_spike    : a single service spiked (data transfer, API calls, etc.)
  - new_resource     : a new expensive resource came online
  - region_expansion : cost appeared in a new region
  - sustained_growth : cost has been growing steadily (not sudden)
  - unknown          : insufficient data for classification
"""
from __future__ import annotations
import datetime
from typing import List, Dict, Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Heuristics configuration
# ─────────────────────────────────────────────────────────────────────────────

_SPIKE_MULTIPLIER = 2.0   # Cost > 2× rolling mean → spike
_GROWTH_DAYS = 5           # N consecutive days of increasing cost → sustained growth


def _rolling_mean(costs: List[float], window: int = 7) -> float:
    if not costs:
        return 0.0
    return sum(costs[-window:]) / len(costs[-window:])


def _classify_root_cause(
    anomaly: Dict[str, Any],
    history: List[Dict[str, Any]],
    idx: int,
) -> Dict[str, Any]:
    """
    Classify the root cause for a single anomaly data point.
    Returns dict with root_cause, impact_score, description, suggested_actions.
    """
    cost = float(anomaly.get("cost", 0.0))
    expected = float(anomaly.get("expected_cost", cost * 0.7))
    severity = anomaly.get("severity", "low")
    date_str = anomaly.get("date", "")
    consecutive = int(anomaly.get("consecutive_anomaly_days", 1))

    # Build a costs-only list up to this anomaly
    prior_costs = [float(h.get("cost", 0.0)) for h in history[:idx]]
    rolling = _rolling_mean(prior_costs, window=7)

    # ── Classify ──────────────────────────────────────────────────────────────
    root_cause = "unknown"
    description = ""
    suggested_actions: List[str] = []
    impact_score = min(round((cost - expected) / max(expected, 1) * 100, 1), 500.0)

    if consecutive >= _GROWTH_DAYS:
        root_cause = "sustained_growth"
        description = (
            f"Cost has been increasing for {consecutive} consecutive days. "
            "This suggests organic growth, a new recurring service, or a slowly scaling workload."
        )
        suggested_actions = [
            "Check for autoscaling groups expanding without bound.",
            "Review new services launched in the past week.",
            "Set a budget alert at your current baseline + 20%.",
            "Forecast next 30 days and confirm growth matches expectations.",
        ]

    elif rolling > 0 and cost >= rolling * _SPIKE_MULTIPLIER:
        root_cause = "service_spike"
        description = (
            f"Cost spiked to ${cost:.2f} (rolling mean: ${rolling:.2f}), "
            f"a {impact_score:.0f}% increase above baseline. "
            "Likely caused by a data transfer surge, unexpected API burst, or misconfigured resource."
        )
        suggested_actions = [
            "Check CloudWatch / Cloud Monitoring for traffic spikes on the anomaly date.",
            "Review data transfer egress costs — often the hidden culprit.",
            "Look for orphaned snapshots or accidental large object uploads.",
            "Enable AWS Cost Anomaly Detection or GCP billing alerts for this service.",
        ]

    elif idx == 0 or (prior_costs and cost > max(prior_costs) * 1.5):
        root_cause = "new_resource"
        description = (
            f"Cost of ${cost:.2f} on {date_str} is significantly higher than all prior readings. "
            "This often indicates a new high-cost resource (e.g. GPU instance, large DB) came online."
        )
        suggested_actions = [
            "Audit resource inventory for resources created around this date.",
            "Check for accidental provisioning of expensive instance types.",
            "Tag all new resources with team/project labels immediately.",
            "Set a maximum instance type policy via AWS Service Control Policies or GCP Org Policy.",
        ]

    else:
        root_cause = "unknown"
        description = (
            f"Anomaly detected at ${cost:.2f} on {date_str}. "
            "Root cause could not be automatically determined — insufficient contextual data."
        )
        suggested_actions = [
            "Manually review the cloud billing console for the anomalous date.",
            "Check for changes in usage patterns via Cost Explorer or BigQuery billing.",
            "Enable detailed cost allocation tags for better future attribution.",
        ]

    return {
        "date": date_str,
        "actual_cost": round(cost, 2),
        "expected_cost": round(expected, 2),
        "deviation_pct": round(impact_score, 1),
        "severity": severity,
        "root_cause": root_cause,
        "description": description,
        "suggested_actions": suggested_actions,
        "consecutive_anomaly_days": consecutive,
    }


def explain_anomalies(
    anomaly_history: List[Dict[str, Any]],
    full_history: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Given the output of CostAnomalyDetector.detect_anomalies(), return
    only the anomalous rows enriched with root-cause explanations.

    Args:
        anomaly_history: full detect_anomalies() output (includes non-anomalies too)
        full_history:    optional raw history for context; falls back to anomaly_history
    """
    history_ref = full_history if full_history else anomaly_history
    explanations = []

    for idx, entry in enumerate(anomaly_history):
        if not entry.get("is_anomaly", False):
            continue
        explanation = _classify_root_cause(entry, history_ref, idx)
        explanations.append(explanation)

    # Sort: most severe deviation first
    explanations.sort(key=lambda e: -e["deviation_pct"])
    return explanations


def explain_single(
    date_str: str,
    anomaly_history: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Explain the anomaly for a specific date. Returns None if no anomaly found.
    """
    for idx, entry in enumerate(anomaly_history):
        if entry.get("date") == date_str and entry.get("is_anomaly", False):
            return _classify_root_cause(entry, anomaly_history, idx)
    return None
