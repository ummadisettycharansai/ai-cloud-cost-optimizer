"""
ML Model Training Pipeline
Retrains IsolationForest (anomaly) and Prophet (forecast) models
on the latest available cost history data.

Called via Celery worker on a schedule.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import pandas as pd  # pyre-ignore[21]
    from sklearn.ensemble import IsolationForest  # pyre-ignore[21]
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from prophet import Prophet  # pyre-ignore[21]
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

from ml_pipeline.feature_engineering import extract_features  # pyre-ignore[21]
from ml_pipeline.model_registry import ModelRegistry  # pyre-ignore[21]


def train_anomaly_model(raw_data: List[Dict]) -> bool:
    """
    Trains IsolationForest on enriched features and saves to model registry.
    Returns True if training succeeded.
    """
    if not SKLEARN_AVAILABLE or len(raw_data) < 10:
        logger.warning("Skipping anomaly model training: insufficient data or sklearn unavailable.")
        return False

    features = extract_features(raw_data)
    df = pd.DataFrame(features)
    X = df[["cost", "rolling_mean", "rolling_std", "z_score", "day_of_week"]].fillna(0).values

    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X)

    registry = ModelRegistry()
    registry.save("anomaly_detector", model)
    logger.info(f"Anomaly model retrained on {len(raw_data)} records.")
    return True


def train_forecast_model(raw_data: List[Dict]) -> bool:
    """
    Trains Prophet on the latest cost time-series and persists it.
    Returns True if training succeeded.
    """
    if not PROPHET_AVAILABLE or len(raw_data) < 14:
        logger.warning("Skipping forecast model training: insufficient data or Prophet unavailable.")
        return False

    df = pd.DataFrame(raw_data)[["date", "cost"]].rename(columns={"date": "ds", "cost": "y"})
    df["ds"] = pd.to_datetime(df["ds"])

    model = Prophet(weekly_seasonality=True, yearly_seasonality=False, daily_seasonality=False)
    model.fit(df)

    registry = ModelRegistry()
    registry.save("forecaster", model)
    logger.info(f"Prophet forecast model retrained on {len(raw_data)} records.")
    return True


def run_full_training_pipeline(raw_data: List[Dict]) -> Dict:
    """
    Execute both model training jobs and return a status report.
    """
    return {
        "anomaly_model": train_anomaly_model(raw_data),
        "forecast_model": train_forecast_model(raw_data),
        "records_used": len(raw_data),
    }
