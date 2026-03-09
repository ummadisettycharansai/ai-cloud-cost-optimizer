"""
Enhanced Cost Anomaly Detector — Production FinOps Edition

Improvements over v1:
  - Four-tier severity: low / medium / high / critical
  - Consecutive anomaly day detection (trend flag)
  - Per-service anomaly breakdown support
  - Anomaly score normalization for UI display
"""
import pandas as pd  # pyre-ignore[21]
from sklearn.ensemble import IsolationForest  # pyre-ignore[21]
from typing import List, Dict, Any


class CostAnomalyDetector:
    def __init__(self, contamination: float = 0.05):
        self.model = IsolationForest(contamination=contamination, random_state=42)

    def detect_anomalies(
        self,
        history_data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Expects a list of dicts: [{"date": "2023-10-01", "cost": 150.0}, ...]
        Returns the data enriched with:
          - is_anomaly (bool)
          - anomaly_score (float, 0–1 normalised; higher = more anomalous)
          - severity ("none" | "low" | "medium" | "high" | "critical")
          - expected_cost (7-day rolling mean)
          - consecutive_anomaly_days (int) — how many consecutive days this is an anomaly
        """
        if not history_data or len(history_data) < 5:
            return history_data

        df = pd.DataFrame(history_data)
        X = df[['cost']].values

        preds = self.model.fit_predict(X)
        raw_scores = self.model.decision_function(X)

        # Normalise scores to [0, 1] where 1 = most anomalous
        min_s, max_s = raw_scores.min(), raw_scores.max()
        span = max_s - min_s if max_s != min_s else 1.0
        normalised = [round(float(1.0 - (s - min_s) / span), 4) for s in raw_scores]

        df['is_anomaly'] = preds == -1
        df['anomaly_score'] = normalised

        # Rolling 7-day mean as the "expected" baseline
        df['expected_cost'] = (
            df['cost'].rolling(window=7, min_periods=1).mean().apply(
                lambda x: round(float(x), 2)  # pyre-ignore[6]
            )
        )

        # Statistical thresholds
        mean_cost = df['cost'].mean()
        std_cost = df['cost'].std()

        def get_severity(row):
            if not row['is_anomaly']:
                return 'none'
            deviation = row['cost'] - mean_cost
            if deviation > 4 * std_cost:
                return 'critical'
            elif deviation > 3 * std_cost:
                return 'high'
            elif deviation > 2 * std_cost:
                return 'medium'
            return 'low'

        df['severity'] = df.apply(get_severity, axis=1)

        # Consecutive anomaly days counter
        consecutive = []
        count = 0
        for is_anom in df['is_anomaly']:
            if is_anom:
                count += 1
            else:
                count = 0
            consecutive.append(count)
        df['consecutive_anomaly_days'] = consecutive

        return df.to_dict('records')

    def get_service_anomalies(
        self,
        history_data: List[Dict[str, Any]],
        service_key: str = "service",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Runs anomaly detection per unique service and returns a dict
        keyed by service name with per-service anomaly results.
        """
        if not history_data:
            return {}

        df = pd.DataFrame(history_data)
        if service_key not in df.columns:
            # No service column — fall back to flat detection
            return {"all": self.detect_anomalies(history_data)}

        result: Dict[str, List[Dict[str, Any]]] = {}
        for svc, group in df.groupby(service_key):
            records = group.to_dict('records')
            result[str(svc)] = self.detect_anomalies(records)

        return result
