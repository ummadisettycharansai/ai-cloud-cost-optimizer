"""
Prometheus Metrics + OpenTelemetry Observability
Exposes application metrics for Prometheus scraping and
provides distributed tracing via OpenTelemetry.
"""
import logging

logger = logging.getLogger(__name__)

# --- Prometheus Metrics ---
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST  # pyre-ignore[21]
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Metrics disabled.")

if PROMETHEUS_AVAILABLE:
    # API Request Counters
    api_requests_total = Counter(
        "api_requests_total",
        "Total number of API requests",
        ["method", "endpoint", "status_code"],
    )

    # Cost Anomaly Tracking
    anomalies_detected_total = Counter(
        "anomalies_detected_total",
        "Total number of cost anomalies detected",
        ["cloud_provider", "severity"],
    )

    # Alert Tracking
    alerts_sent_total = Counter(
        "alerts_sent_total",
        "Total number of alerts dispatched",
        ["alert_type", "channel"],
    )

    # Forecast Metrics
    forecast_requests_total = Counter(
        "forecast_requests_total",
        "Total number of forecast API calls",
    )

    # API Latency Histogram
    api_latency_seconds = Histogram(
        "api_latency_seconds",
        "API endpoint response time in seconds",
        ["endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
    )

    # Active Resource Gauge
    active_resources_gauge = Gauge(
        "active_cloud_resources",
        "Number of currently monitored cloud resources",
        ["cloud_provider"],
    )
else:
    # Stub objects when Prometheus is unavailable
    class _NoOpMetric:
        def labels(self, **_): return self
        def inc(self, *_, **__): pass
        def observe(self, *_, **__): pass
        def set(self, *_, **__): pass

    api_requests_total = _NoOpMetric()
    anomalies_detected_total = _NoOpMetric()
    alerts_sent_total = _NoOpMetric()
    forecast_requests_total = _NoOpMetric()
    api_latency_seconds = _NoOpMetric()
    active_resources_gauge = _NoOpMetric()


def get_metrics_response():
    """Return Prometheus metrics in text format for /metrics endpoint."""
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus not installed\n", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST


# --- OpenTelemetry Tracing ---
try:
    from opentelemetry import trace  # pyre-ignore[21]
    from opentelemetry.sdk.trace import TracerProvider  # pyre-ignore[21]
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter  # pyre-ignore[21]
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

def setup_tracing(service_name: str = "ai-cloud-cost-optimizer"):
    """Initialize OpenTelemetry tracer. Call once at application startup."""
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not installed. Distributed tracing disabled.")
        return None

    provider = TracerProvider()
    # Console exporter for dev — replace with OTLP exporter for production
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer(service_name)
    logger.info(f"OpenTelemetry tracer initialized for service '{service_name}'")
    return tracer
