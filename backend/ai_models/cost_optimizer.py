"""
Cloud Cost Optimizer — Multi-Cloud Efficiency Scoring Engine

Provides:
  - efficiency_score per resource (0–100, higher = more efficient)
  - top waste candidates report
  - efficiency summary across providers
"""
from typing import List, Dict, Any, Optional


def _compute_efficiency_score(resource: Dict[str, Any]) -> float:
    """
    Efficiency score (0–100):
      - High cost + Low CPU  → low score (wasteful)
      - High CPU + Lower cost → high score (efficient)
      - Score = cpu_utilization / max(1, log(monthly_cost + 1)) * scaling_factor
    Uses a sigmoid-like normalisation to keep within [0, 100].
    """
    import math

    cpu = float(resource.get('cpu_utilization', 0.0))
    cost = float(resource.get('monthly_cost', 1.0))
    status = resource.get('status', 'running')

    if status in ('stopped', 'terminated', 'deallocated'):
        # Stopped resources that still incur cost are wasteful
        if cost > 0:
            return max(0.0, round(5.0 - min(cost / 10.0, 5.0), 1))
        return 100.0  # Free stopped resource

    if cost <= 0:
        return 90.0  # No cost — very efficient

    # Normalise: cpu_ratio [0,1] / cost_factor
    cost_factor = math.log1p(cost)       # log(cost+1) to dampen large costs
    cost_factor = max(cost_factor, 0.1)

    # Weight CPU participation and penalise idle resources
    cpu_ratio = cpu / 100.0
    raw_score = (cpu_ratio / cost_factor) * 50.0   # Scale to ~0-100 range

    # Bonus for high CPU / reservoir of utilisation
    if cpu > 60:
        raw_score += 10.0
    elif cpu < 10:
        raw_score -= 15.0

    return round(min(max(raw_score, 0.0), 100.0), 1)


class CloudCostOptimizer:
    """Multi-cloud resource efficiency scorer and waste detector."""

    def score_resources(
        self,
        resources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Returns resources list with `efficiency_score` (0–100) added to each entry.
        Lower score = more wasteful = better candidate for optimisation.
        """
        scored = []
        for r in resources:
            r_copy = dict(r)
            r_copy['efficiency_score'] = _compute_efficiency_score(r_copy)
            scored.append(r_copy)
        return scored

    def get_top_waste_candidates(
        self,
        scored_resources: List[Dict[str, Any]],
        top_n: int = 10,
        max_score: float = 50.0,
    ) -> List[Dict[str, Any]]:
        """
        Returns the top_n most wasteful resources:
          - efficiency_score ≤ max_score  AND
          - sorted by (efficiency_score ASC, monthly_cost DESC) so highest-cost waste comes first
        """
        wasteful = [
            r for r in scored_resources
            if r.get('efficiency_score', 100.0) <= max_score
        ]
        wasteful.sort(key=lambda r: (r.get('efficiency_score', 0), -r.get('monthly_cost', 0)))
        return wasteful[:top_n]

    def efficiency_summary(
        self,
        scored_resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        High-level summary broken down by provider.
        """
        if not scored_resources:
            return {
                "total_resources": 0,
                "avg_efficiency_score": 0.0,
                "waste_ratio_pct": 0.0,
                "by_provider": {},
            }

        scores = [r.get('efficiency_score', 0.0) for r in scored_resources]
        avg_score = round(sum(scores) / len(scores), 1)
        wasteful_count = sum(1 for s in scores if s <= 50.0)
        waste_ratio = round(wasteful_count / len(scores) * 100, 1)

        # Per-provider breakdown
        by_provider: Dict[str, Any] = {}
        for r in scored_resources:
            prov = r.get('provider', 'Unknown')
            if prov not in by_provider:
                by_provider[prov] = {
                    "count": 0,
                    "total_cost": 0.0,
                    "avg_efficiency": 0.0,
                    "_scores": [],
                }
            by_provider[prov]["count"] += 1
            by_provider[prov]["total_cost"] += r.get('monthly_cost', 0.0)
            by_provider[prov]["_scores"].append(r.get('efficiency_score', 0.0))

        for prov, data in by_provider.items():
            s_list = data.pop("_scores")
            data["avg_efficiency"] = round(sum(s_list) / len(s_list), 1)
            data["total_cost"] = round(data["total_cost"], 2)

        return {
            "total_resources": len(scored_resources),
            "avg_efficiency_score": avg_score,
            "waste_ratio_pct": waste_ratio,
            "by_provider": by_provider,
        }
