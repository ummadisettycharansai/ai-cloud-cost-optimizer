"""
Kafka Cost Event Consumer — Production FinOps Edition v2

Pipeline:
  CloudWatch → EventBridge → Kafka (cloud-cost-events) → This Consumer
  → persist CostHistory → anomaly detection → budget alerts → alert engine

Event schema (JSON):
{
  "provider": "AWS" | "GCP" | "Azure",
  "service": "Amazon EC2",
  "region": "us-east-1",
  "account_id": "123456789012",
  "daily_cost": 145.50,
  "date": "2024-01-15",
  "timestamp": "2024-01-15T10:00:00Z"
}

Environment:
  KAFKA_BOOTSTRAP_SERVERS — comma-separated broker addresses (default: localhost:9092)
  DATABASE_URL           — SQLAlchemy database URL (default: sqlite:///./cloud_cost.db)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Kafka ─────────────────────────────────────────────────────────────────────
try:
    from kafka import KafkaConsumer  # pyre-ignore[21]
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("kafka-python not installed — consumer unavailable.")

KAFKA_TOPIC = "cloud-cost-events"
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
KAFKA_GROUP_ID = "cost-optimizer-consumers"

# ── Database (lazy import to avoid circular deps when run standalone) ──────────
def _get_db_session():
    """Return a SQLAlchemy session using DATABASE_URL env var."""
    from sqlalchemy import create_engine  # pyre-ignore[21]
    from sqlalchemy.orm import sessionmaker  # pyre-ignore[21]
    db_url = os.getenv("DATABASE_URL", "sqlite:///./cloud_cost.db")
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def _persist_cost_history(event: Dict[str, Any]) -> None:
    """Write a single cost event to the CostHistory table."""
    try:
        # Dynamic import so the module loads correctly both standalone and inside FastAPI
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from models import CostHistory, Base  # pyre-ignore[21]

        db = _get_db_session()
        try:
            date_str = event.get("date", str(datetime.date.today()))
            record = CostHistory(
                date=datetime.datetime.fromisoformat(date_str),
                service_name=event.get("service", "Unknown"),
                region=event.get("region", "global"),
                provider=event.get("provider", "AWS"),
                account_id=event.get("account_id", ""),
                daily_cost=float(event.get("daily_cost") or 0.0),
            )
            db.add(record)
            db.commit()
            logger.info(
                f"Persisted CostHistory: [{event.get('provider')}] "
                f"{event.get('service')} ${event.get('daily_cost')} on {date_str}"
            )
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Failed to persist cost history: {exc}")


def _run_anomaly_detection(db_session, recent_days: int = 60) -> List[Dict[str, Any]]:
    """Fetch recent history from DB and run IsolationForest detection."""
    try:
        from models import CostHistory  # pyre-ignore[21]
        from ai_models.anomaly_detector import CostAnomalyDetector  # pyre-ignore[21]

        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=recent_days)
        rows = db_session.query(CostHistory).filter(CostHistory.date >= cutoff).all()

        if len(rows) < 5:
            return []

        history = [{"date": str(r.date.date()), "cost": r.daily_cost} for r in rows]
        detector = CostAnomalyDetector()
        results = detector.detect_anomalies(history)
        anomalies = [a for a in results if a.get("is_anomaly")]

        if anomalies:
            logger.warning(f"Anomaly detection found {len(anomalies)} anomaly(ies) after new event.")
        return anomalies

    except Exception as exc:
        logger.error(f"Anomaly detection in consumer failed: {exc}")
        return []


def _dispatch_alerts(anomalies: List[Dict[str, Any]]) -> None:
    """Send anomaly results through the alert engine."""
    if not anomalies:
        return
    try:
        from alerts.alert_engine import AlertEngine  # pyre-ignore[21]
        engine = AlertEngine()
        engine.process_anomalies(anomalies)
    except Exception as exc:
        logger.error(f"Alert dispatch failed: {exc}")


def _check_budgets(db_session) -> None:
    """Run budget engine check and log any alerts."""
    try:
        from budgets.budget_engine import check_all_budgets  # pyre-ignore[21]
        alerts = check_all_budgets(db_session)
        for alert in alerts:
            logger.warning(
                f"BUDGET ALERT [{alert['severity'].upper()}] {alert['budget_name']}: "
                f"${alert['current_spend']:.2f} / ${alert['monthly_limit']:.2f} "
                f"({alert['utilization_pct']}%) — EOM forecast: ${alert['forecast_eom']:.2f}"
            )
    except Exception as exc:
        logger.error(f"Budget check failed: {exc}")


def _run_autopilot(db_session) -> None:
    """Evaluate optimization recommendations and run Auto-Remediation."""
    try:
        from models import CloudResource  # pyre-ignore[21]
        import crud  # pyre-ignore[21]
        from optimizer.recommendation_engine import RecommendationEngine  # pyre-ignore[21]
        from remediation.remediation_engine import RemediationEngine  # pyre-ignore[21]

        resources = db_session.query(CloudResource).all()
        active = [
            {
                "resource_id": r.resource_id,
                "service_name": r.service_name,
                "provider": r.provider,
                "status": r.status,
                "cpu_utilization": r.cpu_utilization,
                "monthly_cost": r.monthly_cost
            }
            for r in resources
        ]
        
        recommender = RecommendationEngine()
        recs = recommender.generate_recommendations(active)

        if not recs:
            return

        remediation = RemediationEngine(db_session)
        # For multi-tenant platform, apply to org=1 as the primary demo tenant
        # Real-world would map resources to specific tenants via tags/account_ids
        org_id = 1 
        
        for rec in recs:
            remediation.process_recommendation(org_id, rec)

    except Exception as exc:
        logger.error(f"Autopilot remediation failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────


class CostEventConsumer:
    """
    Long-running Kafka consumer that:
    1. Persists every cloud cost event to CostHistory
    2. Runs anomaly detection after each event
    3. Dispatches alerts for detected anomalies
    4. Checks all active budgets for threshold breaches
    """

    def __init__(self, bootstrap_servers: Optional[List[str]] = None):
        self.consumer = None
        self.enabled = False
        self._stop_event = threading.Event()

        if not KAFKA_AVAILABLE:
            return

        servers = bootstrap_servers or KAFKA_BOOTSTRAP_SERVERS
        try:
            self.consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=servers,
                group_id=KAFKA_GROUP_ID,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
                consumer_timeout_ms=1000,
            )
            self.enabled = True
            logger.info(f"Kafka consumer subscribed to '{KAFKA_TOPIC}' on {servers}")
        except Exception as exc:
            logger.warning(f"Kafka consumer could not connect ({exc}). Consumer disabled.")

    def process_event(self, event: Dict[str, Any]) -> None:
        """
        Full pipeline for a single cost event:
          persist → anomaly_detect → alerts → budget_check
        """
        provider = event.get("provider", event.get("cloud_provider", "Unknown"))
        service = event.get("service", "Unknown")
        region = event.get("region", "global")
        cost = float(event.get("daily_cost") or event.get("cost") or 0.0)

        logger.info(
            f"Event received: [{provider}] {service} @ {region} = ${cost:.2f}"
        )

        # Step 1: Persist to DB
        _persist_cost_history({**event, "provider": provider, "daily_cost": cost})

        # Steps 2-5: Anomaly detection, alerts, budget check, autopilot
        try:
            db = _get_db_session()
            try:
                anomalies = _run_anomaly_detection(db)
                _dispatch_alerts(anomalies)
                _check_budgets(db)
                _run_autopilot(db)
            finally:
                db.close()
        except Exception as exc:
            logger.error(f"Post-persist pipeline error: {exc}")

    def start(self) -> None:
        """Start consuming events in a blocking loop with retry backoff."""
        if not self.enabled or self.consumer is None:
            logger.info("Consumer not running (Kafka unavailable or disabled).")
            return

        retry_delay: int = 1
        logger.info("Cost event consumer starting...")

        while not self._stop_event.is_set():
            try:
                if self.consumer is None:
                    break
                if self.consumer:
                    for message in self.consumer:  # pyre-ignore[29]
                        if self._stop_event.is_set():
                            break
                        try:
                            self.process_event(message.value)
                            retry_delay = 1  # Reset backoff on success
                        except Exception as exc:
                            logger.error(f"Error processing message: {exc}")
            except Exception as exc:
                logger.error(f"Consumer loop error: {exc}. Retrying in {retry_delay}s...")
                time.sleep(float(retry_delay))
                retry_delay = int(min(int(retry_delay) * 2, 60))  # pyre-ignore[6]

        if self.consumer:
            self.consumer.close()  # pyre-ignore[16]
            logger.info("Kafka consumer closed.")

    def start_background(self) -> threading.Thread:
        """Launch consumer as a non-blocking daemon thread."""
        t = threading.Thread(target=self.start, daemon=True, name="kafka-consumer")
        t.start()
        return t

    def stop(self) -> None:
        self._stop_event.set()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    consumer = CostEventConsumer()
    consumer.start()
