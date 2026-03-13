"""
Feature Engineering Pipeline
Transforms raw time-series cost data into features suitable for ML models.
"""
import logging
import statistics
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def compute_rolling_stats(data: List[Dict], window: int = 7) -> List[Dict]:
    """
    Adds rolling mean and std deviation to each data point.
    Input: [{"date": "2024-01-01", "cost": 150.0}, ...]
    Output: same list with added 'rolling_mean', 'rolling_std', 'z_score' fields.
    """
    costs: List[float] = [float(d.get("cost", 0.0)) for d in data]
    enriched = []

    for i, record in enumerate(data):
        start = max(0, i - window + 1)
        window_costs = costs[start : i + 1]  # pyre-ignore[6]

        roll_mean = statistics.mean(window_costs) if window_costs else 0.0
        roll_std = statistics.stdev(window_costs) if len(window_costs) > 1 else 0.0
        z_score = (record.get("cost", 0.0) - roll_mean) / roll_std if roll_std > 0 else 0.0

        enriched.append({
            **record,
            "rolling_mean": round(float(roll_mean), 4),  # pyre-ignore[6]
            "rolling_std": round(float(roll_std), 4),  # pyre-ignore[6]
            "z_score": round(float(z_score), 4),  # pyre-ignore[6]
        })

    return enriched


def compute_day_of_week(data: List[Dict]) -> List[Dict]:
    """
    Appends day_of_week integer (0=Monday, 6=Sunday) to each record.
    """
    import datetime  # lazy import to avoid circular deps

    enriched = []
    for record in data:
        try:
            dt = datetime.datetime.strptime(record["date"], "%Y-%m-%d")
            dow = dt.weekday()
        except Exception:
            dow = 0

        enriched.append({**record, "day_of_week": dow})
    return enriched


def extract_features(raw_data: List[Dict], window: int = 7) -> List[Dict]:
    """
    Full feature engineering pipeline. Consecutive transformations applied in order.
    Returns enriched records ready for training or inference.
    """
    if not raw_data:
        return []

    data = compute_rolling_stats(raw_data, window=window)
    data = compute_day_of_week(data)
    return data


def detect_spikes(data: List[Dict], z_threshold: float = 2.5) -> List[Dict]:
    """
    Returns a filtered list of records whose z_score exceeds the threshold.
    Useful for quick spike detection without a full ML model.
    """
    enriched = compute_rolling_stats(data)
    return [r for r in enriched if abs(r.get("z_score", 0.0)) >= z_threshold]
