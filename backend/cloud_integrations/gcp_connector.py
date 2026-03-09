"""
GCP Cloud Connector — Real Google Cloud SDK integration.

Authentication:
  1. Service Account JSON key (explicit — recommended for multi-project FinOps)
  2. Application Default Credentials (ADC) — GOOGLE_APPLICATION_CREDENTIALS env var

Implements:
  - Billing / Cost Data: get_project_cost() via Cloud Billing API or BigQuery export
  - Compute Remediation: stop_instance(), delete_persistent_disk(), resize_instance()
  - Resource Inventory: list_instances(), list_disks()

Note: Full billing export queries require a BigQuery dataset configured in the GCP project.
If BigQuery export is not set up, cost data falls back to the Cloud Billing API overview.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from .credential_manager import CloudActionError

logger = logging.getLogger(__name__)

# Google Auth
try:
    import google.auth  # pyre-ignore[21]
    import google.auth.credentials  # pyre-ignore[21]
    from google.oauth2 import service_account  # pyre-ignore[21]
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

# Google Cloud Compute
try:
    from googleapiclient import discovery as gcp_discovery  # pyre-ignore[21]
    from googleapiclient.errors import HttpError  # pyre-ignore[21]
    GCP_COMPUTE_AVAILABLE = True
except ImportError:
    GCP_COMPUTE_AVAILABLE = False

# Google Cloud Billing
try:
    from google.cloud import billing as gcp_billing  # pyre-ignore[21]
    GCP_BILLING_AVAILABLE = True
except ImportError:
    GCP_BILLING_AVAILABLE = False

# BigQuery (for billing export queries)
try:
    from google.cloud import bigquery  # pyre-ignore[21]
    GCP_BIGQUERY_AVAILABLE = True
except ImportError:
    GCP_BIGQUERY_AVAILABLE = False

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/compute",
]


class GCPConnector:
    """
    Real GCP integration via google-cloud-compute + google-cloud-bigquery.
    Supports Service Account JSON or ADC authentication.
    """

    def __init__(
        self,
        project_id: str,
        service_account_json: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        bigquery_dataset: Optional[str] = None,
    ) -> None:
        self.project_id = project_id
        self.billing_account_id = billing_account_id
        self.bigquery_dataset = bigquery_dataset  # e.g. "my_project.billing_export"
        self._credentials = None
        self._compute_service = None
        self._billing_client = None
        self._bq_client = None
        self._sa_json_path: Optional[str] = None
        self.is_connected = False

        if not GOOGLE_AUTH_AVAILABLE:
            logger.warning("GCPConnector: google-auth not installed.")
            return

        try:
            if service_account_json:
                # Parse as dict or file path
                if service_account_json.strip().startswith("{"):
                    sa_info = json.loads(service_account_json)
                    self._credentials = service_account.Credentials.from_service_account_info(
                        sa_info, scopes=SCOPES
                    )
                    # Write to temp file for libraries that need a path
                    tf = tempfile.NamedTemporaryFile(
                        mode="w", suffix=".json", delete=False, prefix="gcp_sa_"
                    )
                    json.dump(sa_info, tf)
                    tf.close()
                    self._sa_json_path = tf.name
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._sa_json_path
                else:
                    # Treat as file path
                    self._credentials = service_account.Credentials.from_service_account_file(
                        service_account_json, scopes=SCOPES
                    )
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_json
                    self._sa_json_path = service_account_json

                logger.info("GCPConnector: Loaded Service Account credentials.")
            else:
                # ADC
                self._credentials, _ = google.auth.default(scopes=SCOPES)
                logger.info("GCPConnector: Using Application Default Credentials.")

            # Build compute client
            if GCP_COMPUTE_AVAILABLE:
                self._compute_service = gcp_discovery.build(
                    "compute", "v1", credentials=self._credentials, cache_discovery=False
                )

            # Build billing client
            if GCP_BILLING_AVAILABLE:
                self._billing_client = gcp_billing.CloudBillingClient(
                    credentials=self._credentials
                )

            # Build BigQuery client
            if GCP_BIGQUERY_AVAILABLE:
                self._bq_client = bigquery.Client(
                    project=project_id, credentials=self._credentials
                )

            # Connectivity check
            if self._compute_service:
                self._compute_service.zones().list(project=project_id, maxResults=1).execute()

            self.is_connected = True
            logger.info(f"GCPConnector: Connected — Project {project_id}")

        except Exception as exc:
            logger.warning(f"GCPConnector: Authentication failed ({exc}).")

    def __del__(self):
        # Clean up temp SA JSON file
        if self._sa_json_path and os.path.exists(self._sa_json_path):
            try:
                os.unlink(self._sa_json_path)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Cost Data
    # ─────────────────────────────────────────────────────────────────────────

    def get_project_cost(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Returns daily cost records for the project.
        Queries BigQuery billing export if configured, otherwise returns billing account overview.
        """
        if not self.is_connected:
            return []

        if self.bigquery_dataset and self._bq_client:
            return self._get_cost_from_bigquery(days)

        logger.info("GCPConnector: BigQuery export not configured — using Billing API overview.")
        return self._get_cost_from_billing_api()

    def _get_cost_from_bigquery(self, days: int) -> List[Dict[str, Any]]:
        """Query BigQuery billing export for daily cost breakdown."""
        try:
            query = f"""
                SELECT
                    DATE(usage_start_time) AS usage_date,
                    service.description AS service,
                    location.region AS region,
                    SUM(cost) AS total_cost
                FROM `{self.bigquery_dataset}`
                WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
                  AND project.id = @project_id
                GROUP BY 1, 2, 3
                ORDER BY 1 DESC
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id)
                ]
            )
            results = self._bq_client.query(query, job_config=job_config).result()
            records = []
            for row in results:
                records.append({
                    "date": str(row.usage_date),
                    "service": row.service,
                    "region": row.region or "global",
                    "cost": round(float(row.total_cost), 4),
                    "provider": "GCP",
                    "account_id": self.project_id,
                })
            return records
        except Exception as exc:
            raise CloudActionError(f"GCP BigQuery billing query failed: {exc}") from exc

    def _get_cost_from_billing_api(self) -> List[Dict[str, Any]]:
        """Fallback: return high-level billing info from Cloud Billing API."""
        if not self._billing_client or not self.billing_account_id:
            return []
        try:
            info = self._billing_client.get_billing_account(name=self.billing_account_id)
            return [{
                "date": str(__import__("datetime").date.today()),
                "service": "GCP (Billing Account Overview)",
                "region": "global",
                "cost": 0.0,  # Billing API doesn't expose spend directly
                "provider": "GCP",
                "account_id": info.name,
            }]
        except Exception as exc:
            logger.error(f"GCP Billing API overview error: {exc}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Resource Inventory
    # ─────────────────────────────────────────────────────────────────────────

    def list_instances(self, zone: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all GCE instances. If zone is None, aggregates across all zones."""
        if not self.is_connected or not self._compute_service:
            return []
        try:
            instances = []
            if zone:
                resp = self._compute_service.instances().list(
                    project=self.project_id, zone=zone
                ).execute()
                for inst in resp.get("items", []):
                    instances.append(self._format_instance(inst, zone))
            else:
                resp = self._compute_service.instances().aggregatedList(
                    project=self.project_id
                ).execute()
                for area, data in resp.get("items", {}).items():
                    z = area.split("/")[-1]
                    for inst in data.get("instances", []):
                        instances.append(self._format_instance(inst, z))
            return instances
        except Exception as exc:
            logger.error(f"GCPConnector.list_instances: {exc}")
            return []

    def _format_instance(self, inst: Dict, zone: str) -> Dict[str, Any]:
        return {
            "instance_name": inst.get("name"),
            "zone": zone,
            "machine_type": inst.get("machineType", "").split("/")[-1],
            "status": inst.get("status", "UNKNOWN").lower(),
            "provider": "GCP",
            "project_id": self.project_id,
        }

    def list_disks(self, zone: Optional[str] = None) -> List[Dict[str, Any]]:
        """List persistent disks. If zone is None, aggregates across all zones."""
        if not self.is_connected or not self._compute_service:
            return []
        try:
            disks = []
            if zone:
                resp = self._compute_service.disks().list(
                    project=self.project_id, zone=zone
                ).execute()
                for disk in resp.get("items", []):
                    disks.append(self._format_disk(disk, zone))
            else:
                resp = self._compute_service.disks().aggregatedList(
                    project=self.project_id
                ).execute()
                for area, data in resp.get("items", {}).items():
                    z = area.split("/")[-1]
                    for disk in data.get("disks", []):
                        disks.append(self._format_disk(disk, z))
            return disks
        except Exception as exc:
            logger.error(f"GCPConnector.list_disks: {exc}")
            return []

    def _format_disk(self, disk: Dict, zone: str) -> Dict[str, Any]:
        users = disk.get("users", [])
        return {
            "disk_name": disk.get("name"),
            "zone": zone,
            "size_gb": disk.get("sizeGb"),
            "status": disk.get("status", "UNKNOWN").lower(),
            "users": [u.split("/")[-1] for u in users],
            "is_attached": len(users) > 0,
            "provider": "GCP",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Remediation Actions
    # ─────────────────────────────────────────────────────────────────────────

    def stop_instance(self, zone: str, instance_name: str) -> Dict[str, Any]:
        """
        Stop a GCE instance (RUNNING → TERMINATED).
        Pre-flight: verifies instance is RUNNING before stopping.
        """
        if not self.is_connected or not self._compute_service:
            raise CloudActionError("GCPConnector not connected — cannot stop instance.")

        # Pre-flight
        try:
            inst = self._compute_service.instances().get(
                project=self.project_id, zone=zone, instance=instance_name
            ).execute()
            if inst.get("status") not in ("RUNNING", "STAGING"):
                raise CloudActionError(
                    f"stop_instance: Instance {instance_name} is '{inst.get('status')}', not RUNNING."
                )
        except HttpError as exc:
            raise CloudActionError(f"Instance pre-flight failed: {exc}") from exc

        try:
            op = self._compute_service.instances().stop(
                project=self.project_id, zone=zone, instance=instance_name
            ).execute()
            result = {
                "action": "stop_compute",
                "instance_name": instance_name,
                "zone": zone,
                "operation_id": op.get("name"),
                "status": "stopping",
                "provider": "GCP",
            }
            logger.info(f"[GCPConnector] Stopping instance {instance_name} in {zone}")
            return result
        except HttpError as exc:
            raise CloudActionError(f"stop_instance failed: {exc}") from exc

    def delete_persistent_disk(self, zone: str, disk_name: str) -> Dict[str, Any]:
        """
        Delete a persistent disk.
        Pre-flight: refuses to delete disks that are attached to instances.
        """
        if not self.is_connected or not self._compute_service:
            raise CloudActionError("GCPConnector not connected — cannot delete disk.")

        try:
            disk = self._compute_service.disks().get(
                project=self.project_id, zone=zone, disk=disk_name
            ).execute()
            if disk.get("users"):
                raise CloudActionError(
                    f"delete_persistent_disk: Disk {disk_name} is still attached. Refusing."
                )
        except HttpError as exc:
            raise CloudActionError(f"Disk pre-flight failed: {exc}") from exc

        try:
            op = self._compute_service.disks().delete(
                project=self.project_id, zone=zone, disk=disk_name
            ).execute()
            result = {
                "action": "delete_persistent_disk",
                "disk_name": disk_name,
                "zone": zone,
                "operation_id": op.get("name"),
                "status": "deleting",
                "provider": "GCP",
            }
            logger.info(f"[GCPConnector] Deleting disk {disk_name} in {zone}")
            return result
        except HttpError as exc:
            raise CloudActionError(f"delete_persistent_disk failed: {exc}") from exc

    def resize_instance(
        self, zone: str, instance_name: str, new_machine_type: str
    ) -> Dict[str, Any]:
        """
        Change the machine type of a TERMINATED instance.
        Note: Instance must be stopped first (cannot resize a running VM).
        new_machine_type example: "e2-standard-2"
        """
        if not self.is_connected or not self._compute_service:
            raise CloudActionError("GCPConnector not connected — cannot resize instance.")

        try:
            inst = self._compute_service.instances().get(
                project=self.project_id, zone=zone, instance=instance_name
            ).execute()
            if inst.get("status") != "TERMINATED":
                raise CloudActionError(
                    f"resize_instance: Instance {instance_name} must be TERMINATED to resize. "
                    f"Current status: {inst.get('status')}. Stop it first."
                )
            old_type = inst.get("machineType", "").split("/")[-1]
        except HttpError as exc:
            raise CloudActionError(f"Instance state check failed: {exc}") from exc

        try:
            machine_type_url = (
                f"zones/{zone}/machineTypes/{new_machine_type}"
            )
            op = self._compute_service.instances().setMachineType(
                project=self.project_id,
                zone=zone,
                instance=instance_name,
                body={"machineType": machine_type_url},
            ).execute()
            result = {
                "action": "resize_instance",
                "instance_name": instance_name,
                "zone": zone,
                "old_machine_type": old_type,
                "new_machine_type": new_machine_type,
                "operation_id": op.get("name"),
                "status": "resized",
                "provider": "GCP",
            }
            logger.info(f"[GCPConnector] Resized {instance_name}: {old_type} → {new_machine_type}")
            return result
        except HttpError as exc:
            raise CloudActionError(f"resize_instance failed: {exc}") from exc
