"""
Enhanced Recommendation Engine — Production FinOps Edition

Improvements over v1:
  - GCP and Azure specific recommendations
  - Priority tiers: critical / high / medium / low (by savings magnitude)
  - ROI score: estimated_savings / monthly_cost * 100
  - Payback months: monthly_cost / estimated_savings
  - Cross-provider optimization suggestions
"""
from typing import List, Dict, Any


# Savings magnitude → priority thresholds (USD/month)
_CRITICAL_THRESHOLD = 500.0
_HIGH_THRESHOLD = 200.0
_MEDIUM_THRESHOLD = 50.0


def _priority(savings: float) -> str:
    if savings >= _CRITICAL_THRESHOLD:
        return "critical"
    elif savings >= _HIGH_THRESHOLD:
        return "high"
    elif savings >= _MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _roi_score(savings: float, monthly_cost: float) -> float:
    if monthly_cost <= 0:
        return 0.0
    return round(savings / monthly_cost * 100, 1)


def _payback_months(monthly_cost: float, savings: float) -> float:
    if savings <= 0:
        return 99.0
    return round(min(monthly_cost / savings, 24.0), 1)


def _enrich(rec: Dict[str, Any], monthly_cost: float) -> Dict[str, Any]:
    """Add priority, roi_score, and payback_months to a recommendation dict."""
    savings = rec.get("estimated_savings", 0.0)
    rec["priority"] = _priority(savings)
    rec["roi_score"] = _roi_score(savings, monthly_cost)
    rec["payback_months"] = _payback_months(monthly_cost, savings)
    return rec


class RecommendationEngine:
    def __init__(self):
        pass

    def generate_recommendations(
        self,
        active_resources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []

        for resource in active_resources:
            svc = resource.get('service_name', '')
            status = resource.get('status', 'running')
            cpu = resource.get('cpu_utilization', 100.0)
            cost = resource.get('monthly_cost', 0.0)
            rid = resource.get('resource_id', '')
            provider = resource.get('provider', 'AWS')

            if status in ("stopped", "terminated"):
                continue

            # ── AWS ──────────────────────────────────────────────────────────
            if provider == "AWS":
                if svc == "Amazon EC2":
                    if cpu < 5.0:
                        recommendations.append(_enrich({
                            "resource_id": rid,
                            "service_name": svc,
                            "provider": provider,
                            "recommendation_type": "Shutdown Idle Instance",
                            "description": f"Instance {rid} has <5% CPU. Stop immediately to eliminate cost.",
                            "estimated_savings": round(cost, 2),
                        }, cost))
                    elif cpu < 20.0:
                        savings = round(cost * 0.5, 2)
                        recommendations.append(_enrich({
                            "resource_id": rid,
                            "service_name": svc,
                            "provider": provider,
                            "recommendation_type": "Right-size Instance",
                            "description": f"Instance {rid} is underutilized (<20% CPU). Downgrade instance size.",
                            "estimated_savings": savings,
                        }, cost))
                    elif cpu > 70.0:
                        savings = round(cost * 0.35, 2)
                        recommendations.append(_enrich({
                            "resource_id": rid,
                            "service_name": svc,
                            "provider": provider,
                            "recommendation_type": "Reserved / Spot Migration",
                            "description": f"Instance {rid} has high baseline. Migrate to 1yr Reserved or Spot Fleet.",
                            "estimated_savings": savings,
                        }, cost))

                elif svc == "Amazon S3":
                    savings = round(cost * 0.45, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "S3 Intelligent Tiering / Glacier",
                        "description": f"Bucket {rid}: enable Intelligent Tiering or archive cold data to Glacier.",
                        "estimated_savings": savings,
                    }, cost))

                elif svc == "Amazon RDS" and cost > 200:
                    savings = round(cost * 0.30, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "Database Reserved Instance",
                        "description": f"High RDS cost on {rid}. Purchase Reserved Instance for 30% savings.",
                        "estimated_savings": savings,
                    }, cost))

                elif svc == "AWS Lambda" and cost > 100:
                    savings = round(cost * 0.20, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "Lambda Compute Savings Plan",
                        "description": f"Lambda function {rid} has significant invocation cost. Purchase Compute Savings Plan.",
                        "estimated_savings": savings,
                    }, cost))

                elif svc == "Amazon CloudFront" and cost > 50:
                    savings = round(cost * 0.15, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "CloudFront Security Bundle",
                        "description": f"Distribution {rid}: bundle with AWS Shield for combined discount.",
                        "estimated_savings": savings,
                    }, cost))

                elif svc == "Amazon EKS":
                    savings = round(cost * 0.25, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "EKS Spot Node Groups",
                        "description": f"Cluster {rid}: migrate non-critical workloads to Spot node groups.",
                        "estimated_savings": savings,
                    }, cost))

            # ── GCP ──────────────────────────────────────────────────────────
            elif provider == "GCP":
                if "Compute Engine" in svc:
                    if cpu < 20.0:
                        savings = round(cost * 0.40, 2)
                        recommendations.append(_enrich({
                            "resource_id": rid,
                            "service_name": svc,
                            "provider": provider,
                            "recommendation_type": "GCP Committed Use Discount",
                            "description": f"VM {rid} is underutilized. Purchase 1yr Committed Use Discount.",
                            "estimated_savings": savings,
                        }, cost))
                    elif cpu > 70.0:
                        savings = round(cost * 0.30, 2)
                        recommendations.append(_enrich({
                            "resource_id": rid,
                            "service_name": svc,
                            "provider": provider,
                            "recommendation_type": "GCP Preemptible / Spot VMs",
                            "description": f"VM {rid} has stable high utilization. Switch non-critical workloads to Spot VMs.",
                            "estimated_savings": savings,
                        }, cost))

                elif "Cloud Storage" in svc:
                    savings = round(cost * 0.40, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "GCP Storage Coldline / Archive",
                        "description": f"Bucket {rid}: move infrequently accessed data to Coldline or Archive class.",
                        "estimated_savings": savings,
                    }, cost))

                elif "BigQuery" in svc and cost > 150:
                    savings = round(cost * 0.25, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "BigQuery Flat-rate Pricing",
                        "description": f"Dataset {rid}: switch to flat-rate slots for predictable cost at this spend level.",
                        "estimated_savings": savings,
                    }, cost))

                elif "Kubernetes Engine" in svc:
                    savings = round(cost * 0.20, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "GKE Autopilot Mode",
                        "description": f"Cluster {rid}: evaluate GKE Autopilot to eliminate over-provisioned node pools.",
                        "estimated_savings": savings,
                    }, cost))

            # ── Azure ─────────────────────────────────────────────────────────
            elif provider == "Azure":
                if "Virtual Machines" in svc or "Compute" in svc:
                    if cpu < 20.0:
                        savings = round(cost * 0.45, 2)
                        recommendations.append(_enrich({
                            "resource_id": rid,
                            "service_name": svc,
                            "provider": provider,
                            "recommendation_type": "Azure Reserved VM Instance",
                            "description": f"VM {rid} is underutilized. Purchase 1yr Reserved Instance for up to 45% savings.",
                            "estimated_savings": savings,
                        }, cost))
                    elif cpu > 70.0:
                        savings = round(cost * 0.30, 2)
                        recommendations.append(_enrich({
                            "resource_id": rid,
                            "service_name": svc,
                            "provider": provider,
                            "recommendation_type": "Azure Spot VMs",
                            "description": f"VM {rid} runs steady workloads. Use Azure Spot for non-critical tasks.",
                            "estimated_savings": savings,
                        }, cost))

                elif "Blob Storage" in svc or "Storage" in svc:
                    savings = round(cost * 0.35, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "Azure Blob Cool / Archive Tier",
                        "description": f"Storage {rid}: move cold blobs to Cool or Archive tier.",
                        "estimated_savings": savings,
                    }, cost))

                elif "SQL" in svc and cost > 200:
                    savings = round(cost * 0.30, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "Azure SQL Hybrid Benefit",
                        "description": f"SQL instance {rid}: apply Azure Hybrid Benefit using existing SQL Server licenses.",
                        "estimated_savings": savings,
                    }, cost))

                elif "Kubernetes" in svc:
                    savings = round(cost * 0.20, 2)
                    recommendations.append(_enrich({
                        "resource_id": rid,
                        "service_name": svc,
                        "provider": provider,
                        "recommendation_type": "AKS Spot Node Pools",
                        "description": f"AKS cluster {rid}: add Spot node pools for batch and dev/test workloads.",
                        "estimated_savings": savings,
                    }, cost))

        # Sort: critical → high → medium → low, then by savings descending
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(
            key=lambda r: (priority_order.get(r.get("priority", "low"), 9), -r.get("estimated_savings", 0))
        )

        return recommendations
