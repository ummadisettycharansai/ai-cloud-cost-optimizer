import os
import logging
import datetime
from celery import Celery # pyre-ignore[21]
from celery.schedules import crontab # pyre-ignore[21]

# In Docker environments, REDIS_URL will override localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "cost_optimizer_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

logger = logging.getLogger(__name__)

# Configure Celery Beat schedule
celery_app.conf.beat_schedule = {
    'sync-aws-daily': {
        'task': 'sync_aws_costs_daily',
        'schedule': crontab(hour=2, minute=0), # 2 AM UTC
    },
    'sync-azure-daily': {
        'task': 'sync_azure_costs_daily',
        'schedule': crontab(hour=2, minute=15),
    },
    'sync-gcp-daily': {
        'task': 'sync_gcp_costs_daily',
        'schedule': crontab(hour=2, minute=30),
    },
    'retrain-forecaster': {
        'task': 'retrain_forecaster_model',
        'schedule': crontab(hour=3, minute=0), # 3 AM UTC
    },
    'evaluate-anomalies-hourly': {
        'task': 'evaluate_anomaly_alerts',
        'schedule': crontab(minute=45), # Hourly at :45
    },
}
celery_app.conf.timezone = 'UTC'


def _sync_provider(provider_name: str) -> dict:
    from database import SessionLocal # pyre-ignore[21]
    import crud # pyre-ignore[21]
    from models import CostHistory # pyre-ignore[21]
    from cloud_integrations.credential_manager import get_credential_manager
    from cloud_integrations.aws_connector import AWSConnector  # pyre-ignore[21]
    from cloud_integrations.azure_connector import AzureConnector  # pyre-ignore[21]
    from cloud_integrations.gcp_connector import GCPConnector  # pyre-ignore[21]
    import json
    
    # Try importing kafka for event pushing; gracefully fallback if missing
    try:
        from kafka import KafkaProducer # pyre-ignore[21]
        KAFKA_BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
    except Exception:
        producer = None

    db = SessionLocal()
    mgr = get_credential_manager()
    total_records: int = 0
    accounts_synced: int = 0

    try:
        accounts = [acc for acc in crud.get_cloud_accounts(db) if acc.provider == provider_name and acc.enabled]
        
        for account in accounts:
            try:
                creds = mgr.decrypt(account.credentials_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt creds for account {account.id}: {e}")
                continue
                
            conn = None
            if provider_name == "aws":
                conn = AWSConnector(
                    role_arn=creds.get("role_arn"),
                    access_key=creds.get("access_key"),
                    secret_key=creds.get("secret_key"),
                    region=account.region or "us-east-1"
                )
            elif provider_name == "azure":
                conn = AzureConnector(
                    tenant_id=creds.get("tenant_id"),
                    client_id=creds.get("client_id"),
                    client_secret=creds.get("client_secret"),
                    subscription_id=creds.get("subscription_id")
                )
            elif provider_name == "gcp":
                conn = GCPConnector(
                    project_id=creds.get("project_id"),
                    service_account_json=creds.get("service_account_json")
                )
                
            if not conn or not conn.is_connected:
                logger.warning(f"Failed to connect to {provider_name} for org {account.org_id}")
                continue
                
            # Fetch cost data for yesterday
            try:
                if provider_name == "aws" and conn:
                    cost_data = conn.get_cost_by_service(days=2)
                elif provider_name == "azure" and conn:
                    cost_data = conn.get_cost_data(days=2)
                elif provider_name == "gcp" and conn:
                    cost_data = conn.get_project_cost(days=2)
                else:
                    cost_data = []
            except Exception as e:
                logger.error(f"Failed to fetch {provider_name} costs: {e}")
                continue
                
            for record in cost_data:
                # Store in DB
                date_obj = datetime.datetime.strptime(record["date"], "%Y-%m-%d")
                db_record = CostHistory(
                    date=date_obj,
                    daily_cost=record["cost"],
                    anomaly_score=0.0
                )
                db.add(db_record)
                total_records = int(total_records) + 1  # pyre-ignore[6, 58]
                
                # Push event to Kafka
                if producer:
                    event = {
                        "event_type": "cost_daily_aggregate",
                        "provider": provider_name,
                        "account_id": record.get("account_id"),
                        "service": record.get("service"),
                        "date": record["date"],
                        "cost": record["cost"]
                    }
                    producer.send("cloud-cost-events", event) # pyre-ignore[16]

            # Mark synced
            crud.update_cloud_account_sync_time(db, account.id)
            accounts_synced = int(accounts_synced) + 1  # pyre-ignore[6, 58]

        db.commit()
        if producer:
            producer.flush()  # pyre-ignore[16]
            
    finally:
        db.close()
        
    return {"status": "success", "accounts_synced": accounts_synced, "records_inserted": total_records}

@celery_app.task(name="sync_aws_costs_daily")
def sync_aws_costs_daily():
    logger.info("Executing AWS cloud cost sync worker...")
    return _sync_provider("aws")

@celery_app.task(name="sync_azure_costs_daily")
def sync_azure_costs_daily():
    logger.info("Executing Azure cloud cost sync worker...")
    return _sync_provider("azure")

@celery_app.task(name="sync_gcp_costs_daily")
def sync_gcp_costs_daily():
    logger.info("Executing GCP cloud cost sync worker...")
    return _sync_provider("gcp")

@celery_app.task(name="retrain_forecaster_model")
def retrain_forecaster_model():
    """
    Background job to retrain the Prophet models off-cycle on real DB history.
    """
    logger.info("Retraining forecasting model inside Celery environment...")
    from database import SessionLocal # pyre-ignore[21]
    from models import CostHistory # pyre-ignore[21]
    from ai_models.forecaster import CostForecaster # pyre-ignore[21]
    
    db = SessionLocal()
    try:
        rows = db.query(CostHistory).order_by(CostHistory.date).all()
        history = [{"date": str(r.date.date()), "cost": r.daily_cost} for r in rows]
        if len(history) > 10:
            forecaster = CostForecaster()
            _ = forecaster.forecast_costs(history)
            logger.info(f"Forecaster retrained on {len(history)} records.")
    finally:
        db.close()
    return {"status": "success"}

@celery_app.task(name="evaluate_anomaly_alerts")
def evaluate_anomaly_alerts():
    """
    Background worker that runs hourly to scan recent cost spikes and dispatch 
    Slack webhooks via alert_engine.
    """
    logger.info("Evaluating real anomaly alerts...")
    from database import SessionLocal # pyre-ignore[21]
    from models import CostHistory # pyre-ignore[21]
    from ai_models.anomaly_detector import CostAnomalyDetector # pyre-ignore[21]
    from alerts.alert_engine import AlertEngine # pyre-ignore[21]
    
    db = SessionLocal()
    try:
        rows = db.query(CostHistory).order_by(CostHistory.date).all()
        history = [{"date": str(r.date.date()), "cost": r.daily_cost} for r in rows]
        
        if len(history) >= 7:
            detector = CostAnomalyDetector()
            anomalies_data = detector.detect_anomalies(history)
            anomalies = [a for a in anomalies_data if a.get('is_anomaly')]
            
            if anomalies:
                engine = AlertEngine()
                engine.process_anomalies(anomalies)
                logger.info(f"Processed {len(anomalies)} anomalies for alerting.")
    finally:
        db.close()
    return {"status": "success"}
