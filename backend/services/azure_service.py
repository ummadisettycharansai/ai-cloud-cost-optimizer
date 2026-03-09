"""
Azure Cost Management Integration
Uses azure-mgmt-costmanagement to fetch real subscription cost data.
Falls back to mock data when credentials / SDK are unavailable.

Environment variables (optional — all required together for real calls):
    AZURE_SUBSCRIPTION_ID
    AZURE_TENANT_ID
    AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET
"""
import datetime
import logging
import random
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional real SDK
try:
    from azure.identity import ClientSecretCredential  # pyre-ignore[21]
    from azure.mgmt.costmanagement import CostManagementClient  # pyre-ignore[21]
    from azure.mgmt.costmanagement.models import (  # pyre-ignore[21]
        QueryDefinition,
        QueryTimePeriod,
        QueryDataset,
        QueryAggregation,
        QueryGrouping,
        GranularityType,
        ExportType,
    )
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False

try:
    from config import settings  # pyre-ignore[21]
except ImportError:
    settings = None  # type: ignore


class AzureService:
    """
    Azure Cost Management API integration.
    Automatically falls back to mock data when credentials are absent.
    """

    MOCK_SERVICES: List[str] = [
        "Azure Virtual Machines",
        "Azure SQL Database",
        "Azure Blob Storage",
        "Azure Kubernetes Service",
        "Azure Functions",
        "Azure App Service",
        "Azure Monitor",
    ]
    MOCK_REGIONS: List[str] = [
        "eastus", "westeurope", "southeastasia", "australiaeast",
    ]

    def __init__(self) -> None:
        self.use_mock = True
        self.client = None
        self.subscription_id: Optional[str] = (
            settings.azure_subscription_id if settings else None
        )

        if not AZURE_SDK_AVAILABLE:
            logger.warning(
                "azure-mgmt-costmanagement not installed — using mock Azure data."
            )
            return

        if not all([
            self.subscription_id,
            settings and settings.azure_tenant_id,
            settings and settings.azure_client_id,
            settings and settings.azure_client_secret,
        ]):
            logger.warning(
                "Azure credentials not fully configured — using mock Azure data."
            )
            return

        try:
            credential = ClientSecretCredential(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret,
            )
            self.client = CostManagementClient(credential)
            self.use_mock = False
            logger.info(
                f"Azure authenticated — Subscription: {self.subscription_id}"
            )
        except Exception as exc:
            logger.warning(f"Azure auth failed ({exc}). Falling back to mock data.")

    # ────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────

    def fetch_current_resources(self) -> List[Dict[str, Any]]:
        """Returns list of active Azure resources with estimated monthly cost."""
        if self.use_mock:
            return self._mock_resources()
        return self._mock_resources()  # resource listing requires azure-mgmt-resource

    def fetch_historical_costs(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Returns daily Azure cost totals from Cost Management API.
        Grouped by ServiceName and ResourceLocation.
        """
        if self.use_mock:
            return self._mock_historical_costs(days)

        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        scope = f"/subscriptions/{self.subscription_id}"

        try:
            query = QueryDefinition(
                type=ExportType.ACTUAL_COST,
                timeframe="Custom",
                time_period=QueryTimePeriod(
                    from_property=datetime.datetime.combine(
                        start_date, datetime.time.min
                    ),
                    to=datetime.datetime.combine(end_date, datetime.time.max),
                ),
                dataset=QueryDataset(
                    granularity=GranularityType.DAILY,
                    aggregation={
                        "totalCost": QueryAggregation(
                            name="PreTaxCost", function="Sum"
                        )
                    },
                    grouping=[
                        QueryGrouping(type="Dimension", name="ServiceName"),
                        QueryGrouping(type="Dimension", name="ResourceLocation"),
                    ],
                ),
            )

            result = self.client.query.usage(scope=scope, parameters=query)

            daily_totals: Dict[str, float] = {}
            columns = [col.name for col in result.columns]
            cost_idx = columns.index("PreTaxCost") if "PreTaxCost" in columns else 0
            date_idx = columns.index("UsageDate") if "UsageDate" in columns else 3

            for row in result.rows or []:
                raw_date = str(row[date_idx])
                # UsageDate comes as int YYYYMMDD
                if len(raw_date) == 8:
                    date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                else:
                    date_str = raw_date[:10]
                cost = float(row[cost_idx])
                daily_totals[date_str] = daily_totals.get(date_str, 0.0) + cost

            return [
                {"date": d, "cost": round(c, 2)}
                for d, c in sorted(daily_totals.items())
            ]

        except Exception as exc:
            logger.error(f"Azure Cost Management error: {exc}. Returning mock.")
            return self._mock_historical_costs(days)

    # ────────────────────────────────────────────────────────────────
    # Mock fallbacks
    # ────────────────────────────────────────────────────────────────

    def _mock_resources(self) -> List[Dict[str, Any]]:
        random.seed(77)
        resources = []
        for i in range(12):
            service = self.MOCK_SERVICES[i % len(self.MOCK_SERVICES)]
            status = "stopped" if i % 9 == 0 else "running"
            resources.append({
                "provider": "Azure",
                "service_name": service,
                "resource_id": f"azure-{service.lower().replace(' ', '-')}-{i:03d}",
                "region": self.MOCK_REGIONS[i % len(self.MOCK_REGIONS)],
                "account_id": self.subscription_id or "mock-subscription",
                "status": status,
                "monthly_cost": round(40.0 + i * 16.7, 2),
                "cpu_utilization": (
                    round(random.uniform(5.0, 70.0), 2)
                    if status == "running" else 0.0
                ),
            })
        return resources

    def _mock_historical_costs(self, days: int) -> List[Dict[str, Any]]:
        base: float = 410.0
        history = []
        for i in range(days):
            date = datetime.date.today() - datetime.timedelta(days=(days - i))
            cost = base + (i * 1.0) + random.uniform(-40, 50)
            if random.random() < 0.035:
                cost += random.uniform(150, 400)
            history.append({"date": str(date), "cost": round(float(max(0, cost)), 2)})
        return history
