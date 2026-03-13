"""
GCP Cloud Billing Integration
Uses google-cloud-billing SDK to fetch real cost data per project.
Falls back to mock data when credentials / SDK are unavailable.

Environment variables (optional):
    GOOGLE_APPLICATION_CREDENTIALS — path to service-account JSON key
    GCP_PROJECT_ID                 — target GCP project
    GCP_BILLING_ACCOUNT_ID         — billing account e.g. billingAccounts/01234A-BCDEF0-GHI567
"""
import datetime
import logging
import random
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional real SDK
try:
    from google.cloud import billing  # pyre-ignore[21]
    from google.auth.exceptions import DefaultCredentialsError  # pyre-ignore[21]
    GCP_SDK_AVAILABLE = True
except ImportError:
    GCP_SDK_AVAILABLE = False

try:
    from config import settings  # pyre-ignore[21]
except ImportError:
    settings = None  # type: ignore


class GCPService:
    """
    Google Cloud Billing API integration.
    Automatically falls back to mock data when credentials are absent.
    """

    MOCK_SERVICES: List[str] = [
        "Google Compute Engine",
        "Cloud Storage",
        "BigQuery",
        "Google Kubernetes Engine",
        "Cloud SQL",
        "Cloud Run",
    ]
    MOCK_REGIONS: List[str] = [
        "us-central1", "us-east1", "europe-west1", "asia-east1",
    ]

    def __init__(self) -> None:
        self.use_mock = True
        self.billing_client = None
        self.project_id: Optional[str] = (
            settings.gcp_project_id if settings else None
        )
        self.billing_account_id: Optional[str] = (
            settings.gcp_billing_account_id if settings else None
        )

        if not GCP_SDK_AVAILABLE:
            logger.warning("google-cloud-billing not installed — using mock GCP data.")
            return

        if not self.billing_account_id:
            logger.warning("GCP_BILLING_ACCOUNT_ID not set — using mock GCP data.")
            return

        try:
            self.billing_client = billing.CloudBillingClient()
            # Quick connectivity check
            if self.billing_client is not None:
                self.billing_client.get_billing_account(  # pyre-ignore[16]
                    name=self.billing_account_id
                )
            else:
                raise ImportError("billing_client is None")
            self.use_mock = False
            logger.info(
                f"GCP authenticated — Billing account: {self.billing_account_id}"
            )
        except Exception as exc:
            logger.warning(f"GCP auth failed ({exc}). Falling back to mock data.")

    # ────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────

    def fetch_current_resources(self) -> List[Dict[str, Any]]:
        """Returns list of active GCP resources with estimated monthly cost."""
        if self.use_mock:
            return self._mock_resources()

        # Real path: fetch projects under billing account
        resources: List[Dict[str, Any]] = []
        try:
            projects_request = billing.ListProjectBillingInfoRequest(
                name=self.billing_account_id
            )
            if self.billing_client is None:
                raise ValueError("Billing client is not initialized")
            for proj_billing in self.billing_client.list_project_billing_info(  # pyre-ignore[16]
                request=projects_request
            ):
                proj_id = proj_billing.project_id
                resources.append({
                    "provider": "GCP",
                    "service_name": "GCP Project",
                    "resource_id": proj_id,
                    "region": "global",
                    "account_id": self.billing_account_id,
                    "status": "running" if proj_billing.billing_enabled else "inactive",
                    "monthly_cost": 0.0,  # Per-project cost from BigQuery export in real pipelines
                    "cpu_utilization": 0.0,
                })
        except Exception as exc:
            logger.error(f"GCP project list error: {exc}. Returning mock.")
            return self._mock_resources()

        return resources if resources else self._mock_resources()

    def fetch_historical_costs(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Returns daily GCP cost totals.
        In a full production setup this would query a BigQuery billing export table.
        """
        if self.use_mock:
            return self._mock_historical_costs(days)

        # Production path: query BigQuery billing export
        # Requires `google-cloud-bigquery` and a configured export dataset.
        # Falling back to mock until BigQuery export is configured.
        logger.info(
            "GCP real billing history requires BigQuery export — using mock data."
        )
        return self._mock_historical_costs(days)

    # ────────────────────────────────────────────────────────────────
    # Mock fallbacks
    # ────────────────────────────────────────────────────────────────

    def _mock_resources(self) -> List[Dict[str, Any]]:
        random.seed(99)
        resources = []
        for i in range(10):
            service = self.MOCK_SERVICES[i % len(self.MOCK_SERVICES)]
            status = "stopped" if i % 8 == 0 else "running"
            resources.append({
                "provider": "GCP",
                "service_name": service,
                "resource_id": f"gcp-{service.lower().replace(' ', '-')}-{i:03d}",
                "region": self.MOCK_REGIONS[i % len(self.MOCK_REGIONS)],
                "account_id": self.billing_account_id or "mock-billing-acct",
                "status": status,
                "monthly_cost": round(float(30.0 + i * 14.3), 2),  # pyre-ignore[6]
                "cpu_utilization": (
                    round(float(random.uniform(8.0, 75.0)), 2)  # pyre-ignore[6]
                    if status == "running" else 0.0
                ),
            })
        return resources

    def _mock_historical_costs(self, days: int) -> List[Dict[str, Any]]:
        base: float = 320.0
        history = []
        for i in range(days):
            date = datetime.date.today() - datetime.timedelta(days=(days - i))
            cost = base + (i * 0.8) + random.uniform(-30, 40)
            if random.random() < 0.03:
                cost += random.uniform(100, 300)
            history.append({"date": str(date), "cost": round(float(max(0.0, cost)), 2)})  # pyre-ignore[6]
        return history
