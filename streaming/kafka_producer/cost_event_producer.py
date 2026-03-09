"""
Kafka Cost Event Producer
Publishes real-time cost events from multi-cloud providers to the
'cloud-cost-events' Kafka topic.

Falls back gracefully if Kafka broker is unavailable (e.g. local dev without Docker).
"""
import json
import logging
import datetime

logger = logging.getLogger(__name__)

try:
    from kafka import KafkaProducer  # pyre-ignore[21]
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("kafka-python not installed. Producer running in no-op mode.")

KAFKA_TOPIC = "cloud-cost-events"
KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]


class CostEventProducer:
    """Publishes cost events to Kafka. Safe to instantiate even without a broker."""

    def __init__(self, bootstrap_servers: list = None):
        self.producer = None
        self.enabled = False

        if not KAFKA_AVAILABLE:
            return

        servers = bootstrap_servers or KAFKA_BOOTSTRAP_SERVERS
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
            )
            self.enabled = True
            logger.info(f"Kafka producer connected to {servers}")
        except Exception as exc:
            logger.warning(f"Kafka producer could not connect: {exc}. Running in no-op mode.")

    def publish_cost_event(
        self,
        cloud_provider: str,
        service: str,
        region: str,
        cost: float,
    ) -> bool:
        """
        Push a single cost event to the Kafka topic.

        Returns True if successfully published, False otherwise.
        """
        event = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "cloud_provider": cloud_provider,
            "service": service,
            "region": region,
            "cost": round(cost, 4),
        }

        if not self.enabled or self.producer is None:
            logger.debug(f"[NO-OP] Would publish: {event}")
            return False

        try:
            future = self.producer.send(
                KAFKA_TOPIC,
                key=f"{cloud_provider}:{service}:{region}",
                value=event,
            )
            future.get(timeout=5)
            logger.info(f"Published cost event: {cloud_provider}/{service} ${cost}")
            return True
        except Exception as exc:
            logger.error(f"Failed to publish Kafka event: {exc}")
            return False

    def publish_batch(self, events: list) -> int:
        """Publish a list of cost event dicts. Returns count of successful sends."""
        success = 0
        for e in events:
            ok = self.publish_cost_event(
                cloud_provider=e.get("cloud_provider", "Unknown"),
                service=e.get("service", "Unknown"),
                region=e.get("region", "global"),
                cost=float(e.get("cost", 0.0)),
            )
            if ok:
                success += 1
        return success

    def close(self):
        if self.producer:
            self.producer.flush()
            self.producer.close()

# Default singleton instance
producer = CostEventProducer()
