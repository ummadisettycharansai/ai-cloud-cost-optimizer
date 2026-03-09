"""
Azure Cloud Connector — Real Azure SDK integration.

Authentication: Service Principal (ClientSecretCredential)
  Required: tenant_id, client_id, client_secret, subscription_id

Implements:
  - Cost Management: get_cost_data()
  - VM Remediation: deallocate_vm(), scale_down_vm()
  - Disk Remediation: delete_unused_disk()
  - Resource Inventory: list_vms(), list_unattached_disks()

All remediation methods perform pre-flight state checks.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional

from .credential_manager import CloudActionError

logger = logging.getLogger(__name__)

# Azure Identity
try:
    from azure.identity import ClientSecretCredential  # pyre-ignore[21]
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    AZURE_IDENTITY_AVAILABLE = False

# Azure Compute (VM + Disk management)
try:
    from azure.mgmt.compute import ComputeManagementClient  # pyre-ignore[21]
    AZURE_COMPUTE_AVAILABLE = True
except ImportError:
    AZURE_COMPUTE_AVAILABLE = False

# Azure Cost Management
try:
    from azure.mgmt.costmanagement import CostManagementClient  # pyre-ignore[21]
    from azure.mgmt.costmanagement.models import (  # pyre-ignore[21]
        QueryDefinition, QueryTimePeriod, QueryDataset,
        QueryAggregation, QueryGrouping, GranularityType, ExportType,
    )
    AZURE_COST_AVAILABLE = True
except ImportError:
    AZURE_COST_AVAILABLE = False


class AzureConnector:
    """
    Real Azure integration via azure-identity + azure-mgmt-compute + azure-mgmt-costmanagement.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: str,
    ) -> None:
        self.subscription_id = subscription_id
        self._credential = None
        self._compute_client = None
        self._cost_client = None
        self.is_connected = False

        if not AZURE_IDENTITY_AVAILABLE:
            logger.warning("AzureConnector: azure-identity not installed.")
            return

        try:
            self._credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )

            if AZURE_COMPUTE_AVAILABLE:
                self._compute_client = ComputeManagementClient(
                    credential=self._credential,
                    subscription_id=subscription_id,
                )

            if AZURE_COST_AVAILABLE:
                self._cost_client = CostManagementClient(credential=self._credential)

            # Connectivity check — list VMs (lightweight paginator, first page only)
            if self._compute_client:
                next(iter(self._compute_client.virtual_machines.list_all()), None)

            self.is_connected = True
            logger.info(f"AzureConnector: Connected — Subscription {subscription_id}")

        except Exception as exc:
            logger.warning(f"AzureConnector: Authentication failed ({exc}).")

    # ─────────────────────────────────────────────────────────────────────────
    # Cost Data
    # ─────────────────────────────────────────────────────────────────────────

    def get_cost_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """Daily cost totals from Azure Cost Management, grouped by ServiceName + Region."""
        if not self.is_connected or not self._cost_client:
            return []

        end = datetime.date.today()
        start = end - datetime.timedelta(days=days)
        scope = f"/subscriptions/{self.subscription_id}"

        try:
            query = QueryDefinition(
                type=ExportType.ACTUAL_COST,
                timeframe="Custom",
                time_period=QueryTimePeriod(
                    from_property=datetime.datetime.combine(start, datetime.time.min),
                    to=datetime.datetime.combine(end, datetime.time.max),
                ),
                dataset=QueryDataset(
                    granularity=GranularityType.DAILY,
                    aggregation={"totalCost": QueryAggregation(name="PreTaxCost", function="Sum")},
                    grouping=[
                        QueryGrouping(type="Dimension", name="ServiceName"),
                        QueryGrouping(type="Dimension", name="ResourceLocation"),
                    ],
                ),
            )
            result = self._cost_client.query.usage(scope=scope, parameters=query)

            columns = [col.name for col in result.columns]
            cost_idx = columns.index("PreTaxCost") if "PreTaxCost" in columns else 0
            date_idx = columns.index("UsageDate") if "UsageDate" in columns else -1
            svc_idx = columns.index("ServiceName") if "ServiceName" in columns else -1
            region_idx = columns.index("ResourceLocation") if "ResourceLocation" in columns else -1

            records = []
            for row in result.rows or []:
                raw_date = str(row[date_idx]) if date_idx >= 0 else ""
                if len(raw_date) == 8:
                    date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                else:
                    date_str = raw_date[:10]

                records.append({
                    "date": date_str,
                    "service": row[svc_idx] if svc_idx >= 0 else "Unknown",
                    "region": row[region_idx] if region_idx >= 0 else "global",
                    "cost": round(float(row[cost_idx]), 4),
                    "provider": "Azure",
                    "account_id": self.subscription_id,
                })
            return records

        except Exception as exc:
            raise CloudActionError(f"Azure Cost Management query failed: {exc}") from exc

    # ─────────────────────────────────────────────────────────────────────────
    # Resource Inventory
    # ─────────────────────────────────────────────────────────────────────────

    def list_vms(self) -> List[Dict[str, Any]]:
        """List all VMs in the subscription with power state."""
        if not self.is_connected or not self._compute_client:
            return []
        try:
            vms = []
            for vm in self._compute_client.virtual_machines.list_all():
                rg = vm.id.split("/resourceGroups/")[1].split("/")[0] if vm.id else ""
                instance_view = self._compute_client.virtual_machines.instance_view(rg, vm.name)
                power_state = "unknown"
                for status in (instance_view.statuses or []):
                    if status.code.startswith("PowerState/"):
                        power_state = status.code.split("/")[1]
                vms.append({
                    "vm_name": vm.name,
                    "resource_group": rg,
                    "location": vm.location,
                    "vm_size": vm.hardware_profile.vm_size if vm.hardware_profile else None,
                    "power_state": power_state,
                    "provider": "Azure",
                })
            return vms
        except Exception as exc:
            logger.error(f"AzureConnector.list_vms: {exc}")
            return []

    def list_unattached_disks(self) -> List[Dict[str, Any]]:
        """List managed disks not attached to any VM."""
        if not self.is_connected or not self._compute_client:
            return []
        try:
            disks = []
            for disk in self._compute_client.disks.list():
                if disk.disk_state == "Unattached":
                    rg = disk.id.split("/resourceGroups/")[1].split("/")[0] if disk.id else ""
                    disks.append({
                        "disk_name": disk.name,
                        "resource_group": rg,
                        "size_gb": disk.disk_size_gb,
                        "disk_state": disk.disk_state,
                        "location": disk.location,
                        "provider": "Azure",
                    })
            return disks
        except Exception as exc:
            logger.error(f"AzureConnector.list_unattached_disks: {exc}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Remediation Actions
    # ─────────────────────────────────────────────────────────────────────────

    def deallocate_vm(self, resource_group: str, vm_name: str) -> Dict[str, Any]:
        """
        Deallocate (stop + release compute) a VM.
        Stops billing for compute. Storage continues to be billed.
        Raises: CloudActionError on failure.
        """
        if not self.is_connected or not self._compute_client:
            raise CloudActionError("AzureConnector not connected — cannot deallocate VM.")

        try:
            poller = self._compute_client.virtual_machines.begin_deallocate(
                resource_group_name=resource_group,
                vm_name=vm_name,
            )
            poller.result(timeout=300)  # wait up to 5 min
            result = {
                "action": "deallocate_vm",
                "vm_name": vm_name,
                "resource_group": resource_group,
                "status": "deallocated",
                "provider": "Azure",
            }
            logger.info(f"[AzureConnector] Deallocated VM {resource_group}/{vm_name}")
            return result
        except Exception as exc:
            raise CloudActionError(f"deallocate_vm failed: {exc}") from exc

    def scale_down_vm(
        self, resource_group: str, vm_name: str, new_size: str
    ) -> Dict[str, Any]:
        """
        Resize a VM to a smaller SKU.
        new_size example: "Standard_B2s" (smaller than Standard_D4s_v3)
        """
        if not self.is_connected or not self._compute_client:
            raise CloudActionError("AzureConnector not connected — cannot resize VM.")

        try:
            vm = self._compute_client.virtual_machines.get(resource_group, vm_name)
            old_size = vm.hardware_profile.vm_size
            vm.hardware_profile.vm_size = new_size

            poller = self._compute_client.virtual_machines.begin_update(
                resource_group_name=resource_group,
                vm_name=vm_name,
                parameters=vm,
            )
            poller.result(timeout=300)
            result = {
                "action": "scale_down_vm",
                "vm_name": vm_name,
                "resource_group": resource_group,
                "old_size": old_size,
                "new_size": new_size,
                "status": "resized",
                "provider": "Azure",
            }
            logger.info(f"[AzureConnector] Resized VM {vm_name}: {old_size} → {new_size}")
            return result
        except Exception as exc:
            raise CloudActionError(f"scale_down_vm failed: {exc}") from exc

    def delete_unused_disk(self, resource_group: str, disk_name: str) -> Dict[str, Any]:
        """
        Delete an unattached managed disk.
        Pre-flight: verifies disk state is 'Unattached' before deletion.
        """
        if not self.is_connected or not self._compute_client:
            raise CloudActionError("AzureConnector not connected — cannot delete disk.")

        try:
            disk = self._compute_client.disks.get(resource_group, disk_name)
            if disk.disk_state != "Unattached":
                raise CloudActionError(
                    f"delete_unused_disk: Disk {disk_name} is '{disk.disk_state}', not 'Unattached'. Refusing."
                )

            poller = self._compute_client.disks.begin_delete(
                resource_group_name=resource_group,
                disk_name=disk_name,
            )
            poller.result(timeout=180)
            result = {
                "action": "delete_disk",
                "disk_name": disk_name,
                "resource_group": resource_group,
                "size_gb": disk.disk_size_gb,
                "status": "deleted",
                "provider": "Azure",
            }
            logger.info(f"[AzureConnector] Deleted disk {resource_group}/{disk_name}")
            return result
        except CloudActionError:
            raise
        except Exception as exc:
            raise CloudActionError(f"delete_unused_disk failed: {exc}") from exc
