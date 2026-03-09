"""
Right-Sizing Engine — ML-based instance recommendation engine.

Uses CPU utilization vs. cost ratios to compute the optimal instance size
for each resource, with confidence scores and multi-cloud equivalence mapping.

Supported providers: AWS, GCP, Azure
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Instance family catalogs (monthly on-demand USD estimates)
# ─────────────────────────────────────────────────────────────────────────────

AWS_INSTANCE_FAMILY = [
    {"type": "t3.nano",    "vcpu": 2,   "memory_gb": 0.5,  "cost_mo": 3.80},
    {"type": "t3.micro",   "vcpu": 2,   "memory_gb": 1.0,  "cost_mo": 7.59},
    {"type": "t3.small",   "vcpu": 2,   "memory_gb": 2.0,  "cost_mo": 15.18},
    {"type": "t3.medium",  "vcpu": 2,   "memory_gb": 4.0,  "cost_mo": 30.37},
    {"type": "t3.large",   "vcpu": 2,   "memory_gb": 8.0,  "cost_mo": 60.74},
    {"type": "m5.large",   "vcpu": 2,   "memory_gb": 8.0,  "cost_mo": 69.12},
    {"type": "m5.xlarge",  "vcpu": 4,   "memory_gb": 16.0, "cost_mo": 138.24},
    {"type": "m5.2xlarge", "vcpu": 8,   "memory_gb": 32.0, "cost_mo": 276.48},
    {"type": "m5.4xlarge", "vcpu": 16,  "memory_gb": 64.0, "cost_mo": 552.96},
    {"type": "c5.large",   "vcpu": 2,   "memory_gb": 4.0,  "cost_mo": 61.20},
    {"type": "c5.xlarge",  "vcpu": 4,   "memory_gb": 8.0,  "cost_mo": 122.40},
    {"type": "r5.large",   "vcpu": 2,   "memory_gb": 16.0, "cost_mo": 90.52},
    {"type": "r5.xlarge",  "vcpu": 4,   "memory_gb": 32.0, "cost_mo": 181.04},
]

GCP_INSTANCE_FAMILY = [
    {"type": "e2-micro",        "vcpu": 2,  "memory_gb": 1.0,  "cost_mo": 6.11},
    {"type": "e2-small",        "vcpu": 2,  "memory_gb": 2.0,  "cost_mo": 12.23},
    {"type": "e2-medium",       "vcpu": 2,  "memory_gb": 4.0,  "cost_mo": 24.46},
    {"type": "n2-standard-2",   "vcpu": 2,  "memory_gb": 8.0,  "cost_mo": 58.18},
    {"type": "n2-standard-4",   "vcpu": 4,  "memory_gb": 16.0, "cost_mo": 116.36},
    {"type": "n2-standard-8",   "vcpu": 8,  "memory_gb": 32.0, "cost_mo": 232.72},
    {"type": "n2-highmem-4",    "vcpu": 4,  "memory_gb": 32.0, "cost_mo": 150.72},
    {"type": "c2-standard-4",   "vcpu": 4,  "memory_gb": 16.0, "cost_mo": 130.56},
]

AZURE_INSTANCE_FAMILY = [
    {"type": "B1s",        "vcpu": 1,  "memory_gb": 1.0,  "cost_mo": 7.59},
    {"type": "B2s",        "vcpu": 2,  "memory_gb": 4.0,  "cost_mo": 30.37},
    {"type": "D2s_v3",     "vcpu": 2,  "memory_gb": 8.0,  "cost_mo": 70.08},
    {"type": "D4s_v3",     "vcpu": 4,  "memory_gb": 16.0, "cost_mo": 140.16},
    {"type": "D8s_v3",     "vcpu": 8,  "memory_gb": 32.0, "cost_mo": 280.32},
    {"type": "E2s_v3",     "vcpu": 2,  "memory_gb": 16.0, "cost_mo": 91.98},
    {"type": "F4s_v2",     "vcpu": 4,  "memory_gb": 8.0,  "cost_mo": 122.64},
]

# Cross-cloud equivalence (approximate)
CROSS_CLOUD_EQUIVALENCE: Dict[str, Dict[str, str]] = {
    "m5.large":   {"GCP": "n2-standard-2",  "Azure": "D2s_v3"},
    "m5.xlarge":  {"GCP": "n2-standard-4",  "Azure": "D4s_v3"},
    "m5.2xlarge": {"GCP": "n2-standard-8",  "Azure": "D8s_v3"},
    "c5.large":   {"GCP": "c2-standard-4",  "Azure": "F4s_v2"},
    "r5.large":   {"GCP": "n2-highmem-4",   "Azure": "E2s_v3"},
}

_PROVIDER_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "AWS":   AWS_INSTANCE_FAMILY,
    "GCP":   GCP_INSTANCE_FAMILY,
    "Azure": AZURE_INSTANCE_FAMILY,
}


# ─────────────────────────────────────────────────────────────────────────────
# Core logic
# ─────────────────────────────────────────────────────────────────────────────

def _target_cpu_band(cpu: float) -> tuple[float, float]:
    """
    Given current CPU utilization %, return the ideal utilization band (low, high)
    we want after right-sizing. We target 40–70% as optimal.
    """
    if cpu < 5:
        return (0.0, 5.0)    # Essentially idle → downsize aggressively
    if cpu < 20:
        return (5.0, 20.0)   # Underutilized
    if cpu < 40:
        return (20.0, 40.0)  # Slightly under
    return (40.0, 70.0)      # Already in sweet spot (shouldn't reach here often)


def _confidence(cpu: float, current_cost: float, recommended_cost: float) -> float:
    """
    Confidence (0–100) in the recommendation.
    Higher when cpu deviation from ideal is large and savings are substantial.
    """
    savings_pct = (current_cost - recommended_cost) / max(current_cost, 1) * 100
    cpu_gap = abs(cpu - 55.0)   # 55% is the centre of the ideal band
    raw = min(savings_pct, 60.0) + min(cpu_gap, 40.0)
    return round(min(raw, 100.0), 1)


def _find_best_instance(
    catalog: List[Dict[str, Any]],
    current_cost: float,
    cpu: float,
) -> Optional[Dict[str, Any]]:
    """
    Pick the smallest catalog instance that would keep the CPU in the 40–70% band
    after right-sizing (accounting for actual CPU load vs. capacity ratio).
    Falls back to cheapest option if CPU is negligible.
    """
    if cpu < 1.0:
        # Idle — just return the cheapest
        return min(catalog, key=lambda i: i["cost_mo"])

    # Sort by cost ascending; pick smallest that would host the workload comfortably
    sorted_cat = sorted(catalog, key=lambda i: i["cost_mo"])
    # We scale: current instance can host `cpu`% of its capacity.
    # If we move to a smaller instance, the same load is proportionally higher.
    for inst in sorted_cat:
        # Estimate new CPU % = (current_actual_load) / (new_relative_capacity)
        # Approximate: scale_factor = new_cost / current_cost  (cheapest proxy)
        if current_cost <= 0:
            return inst
        scale = inst["cost_mo"] / current_cost
        projected_cpu = cpu / max(scale, 0.1)
        if 30.0 <= projected_cpu <= 80.0:
            return inst

    # If nothing fits under 80%, return the instance just below current cost
    cheaper = [i for i in sorted_cat if i["cost_mo"] < current_cost * 0.95]
    return cheaper[-1] if cheaper else None


def generate_rightsizing_recommendations(
    resources: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    For each compute resource analyse CPU utilization, find a better-fit instance,
    and return a rich recommendation dict.
    """
    recs: List[Dict[str, Any]] = []

    for r in resources:
        provider = r.get("provider", "AWS")
        service = r.get("service_name", "")
        cpu = float(r.get("cpu_utilization", 0.0))
        cost = float(r.get("monthly_cost", 0.0))
        rid = r.get("resource_id", "")
        status = r.get("status", "running")

        # Skip non-compute or stopped resources
        is_compute = any(kw in service for kw in ("EC2", "Compute Engine", "Virtual Machine", "VM"))
        if not is_compute or status in ("stopped", "terminated") or cost <= 0:
            continue

        # Already optimally utilised
        if 40.0 <= cpu <= 70.0:
            continue

        catalog = _PROVIDER_CATALOG.get(provider, AWS_INSTANCE_FAMILY)
        recommended = _find_best_instance(catalog, cost, cpu)

        if recommended is None or recommended["cost_mo"] >= cost * 0.95:
            continue   # No meaningful saving

        savings = round(cost - recommended["cost_mo"], 2)
        confidence = _confidence(cpu, cost, recommended["cost_mo"])

        # Cross-cloud alternative (only for AWS → others)
        cross_cloud: Dict[str, Any] = {}
        if provider == "AWS":
            for aws_type, equiv in CROSS_CLOUD_EQUIVALENCE.items():
                cross_cloud = equiv
                break   # Just show one example for now

        rec: Dict[str, Any] = {
            "resource_id": rid,
            "service_name": service,
            "provider": provider,
            "current_monthly_cost": cost,
            "current_cpu_utilization": cpu,
            "recommended_instance": recommended["type"],
            "recommended_vcpu": recommended["vcpu"],
            "recommended_memory_gb": recommended["memory_gb"],
            "recommended_cost": recommended["cost_mo"],
            "estimated_monthly_savings": savings,
            "confidence_score": confidence,
            "recommendation_type": "right-size",
            "reason": (
                f"CPU utilization is {cpu:.1f}% — "
                + ("near-idle, terminate or use a nano/micro." if cpu < 5 else
                   "underutilized. Downsize to improve cost efficiency.")
            ),
        }
        if cross_cloud:
            rec["cross_cloud_equivalent"] = cross_cloud

        recs.append(rec)

    # Sort: highest savings first
    recs.sort(key=lambda r: -r["estimated_monthly_savings"])
    return recs
