import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session # pyre-ignore[21]
import crud # pyre-ignore[21]
import requests
from models import AutopilotAction # pyre-ignore[21]

from cloud_integrations.credential_manager import get_credential_manager, CloudActionError
from cloud_integrations.aws_connector import AWSConnector
from cloud_integrations.azure_connector import AzureConnector
from cloud_integrations.gcp_connector import GCPConnector

logger = logging.getLogger(__name__)

class RemediationEngine:
    """
    Cost Autopilot: Analyzes optimization recommendations and automatically
    executes remediation actions (mocked APIs for AWS/Azure/GCP) if the
    tenant organization's safety policies allow it.
    """
    def __init__(self, db_session: Session):
        self.db = db_session

    def process_recommendation(self, org_id: int, rec: Dict[str, Any]) -> getattr(crud, "Optional", None)[AutopilotAction]: # type: ignore
        """
        Evaluate a single recommendation and attempt auto-remediation.
        `rec` expects keys: resource_id, service_name, recommendation_type, estimated_savings
        """
        provider = rec.get("provider", self._guess_provider(rec.get("service_name", "")))
        action_type = rec.get("recommendation_type", "")
        resource_id = rec.get("resource_id", "unknown")
        savings = float(rec.get("estimated_savings", 0.0))

        logger.info(f"[AUTOPILOT] Analyzing recommendation for {resource_id}: {action_type} (Saving ${savings}/mo)")

        # 1. Safety Check: Verify Policy
        policy = crud.get_autopilot_policy(self.db, org_id)
        if not policy or not policy.enabled:
            logger.info(f"[AUTOPILOT] Skipped: Autopilot is disabled for Org {org_id}.")
            return

        # 2. Safety Check: Daily Limits
        daily_count = crud.get_daily_action_count(self.db, org_id)
        if daily_count >= policy.max_daily_actions:
            logger.warning(f"[AUTOPILOT] Skipped: Daily action limit reached ({daily_count}/{policy.max_daily_actions}) for Org {org_id}.")
            return
            
        # 3. Safety Check: Action Type Allowed
        allowed = [a.strip().lower() for a in policy.allowed_actions.split(",")]
        normalized_action = self._normalize_action_type(action_type)
        if normalized_action not in allowed:
            logger.warning(f"[AUTOPILOT] Skipped: Action '{normalized_action}' is not in allowed list for Org {org_id}.")
            return None

        # 4. Execute Remediation (Mock or Real)
        status = self._execute_cloud_action(org_id, provider, action_type, resource_id)

        # 5. Log Execution
        action_data = {
            "org_id": org_id,
            "provider": provider,
            "resource_id": resource_id,
            "action": action_type,
            "status": status,
            "estimated_savings": savings
        }
        crud.log_autopilot_action(self.db, action_data)
        logger.info(f"[AUTOPILOT] Executed: {action_type} on {resource_id} (Status: {status})")

        # 6. Notify
        if status in ("success", "simulated"):
            self._send_notification(
                f"🤖 *Autopilot Action:* Executed `{action_type}` on resource `{resource_id}` ({status}). Estimated monthly savings: **${savings:.2f}**"
            )
            
        return action


    def _execute_cloud_action(self, org_id: int, provider: str, action: str, resource_id: str) -> str:
        """Call real cloud provider APIs if configured, otherwise fallback to mock simulation."""
        provider_lower = provider.lower()
        account = crud.get_cloud_account_by_org_provider(self.db, org_id, provider_lower)
        
        if not account:
            logger.warning(f"-> [SIMULATED] No {provider} credentials configured for org {org_id}. Mocking action '{action}' on {resource_id}.")
            return "simulated"
            
        mgr = get_credential_manager()
        try:
            creds = mgr.decrypt(account.credentials_encrypted)
        except Exception as exc:
            logger.error(f"Failed to decrypt credentials for org {org_id} {provider}: {exc}")
            return "failed"
            
        try:
            if provider_lower == "aws":
                conn = AWSConnector(
                    role_arn=creds.get("role_arn"),
                    access_key=creds.get("access_key"),
                    secret_key=creds.get("secret_key"),
                    region=account.region or "us-east-1"
                )
                if not conn.is_connected:
                    return "simulated"
                
                if "stop" in action and "ec2" in action:
                    conn.stop_ec2_instance(resource_id)
                elif "delete" in action and "ebs" in action:
                    conn.delete_ebs_volume(resource_id)
                elif "glacier" in action:
                    bucket = resource_id.split("/")[0] if "/" in resource_id else resource_id
                    conn.move_s3_to_glacier(bucket)
                else:
                    return "skipped"

            elif provider_lower == "azure":
                conn = AzureConnector(
                    tenant_id=creds.get("tenant_id"),
                    client_id=creds.get("client_id"),
                    client_secret=creds.get("client_secret"),
                    subscription_id=creds.get("subscription_id")
                )
                if not conn.is_connected:
                    return "simulated"
                    
                rg = "default-rg"
                parts = resource_id.split("/")
                if "resourceGroups" in parts:
                    rg = parts[parts.index("resourceGroups") + 1]
                name = parts[-1]
                
                if "deallocate" in action or "stop" in action:
                    conn.deallocate_vm(rg, name)
                elif "scale" in action:
                    conn.scale_down_vm(rg, name, "Standard_B2s") # hardcoded default fallback
                elif "delete" in action:
                    conn.delete_unused_disk(rg, name)
                else:
                    return "skipped"
                    
            elif provider_lower == "gcp":
                conn = GCPConnector(
                    project_id=creds.get("project_id"),
                    service_account_json=creds.get("service_account_json")
                )
                if not conn.is_connected:
                    return "simulated"
                    
                zone = "us-central1-a"
                parts = resource_id.split("/")
                if "zones" in parts:
                    zone = parts[parts.index("zones") + 1]
                name = parts[-1]
                
                if "stop" in action:
                    conn.stop_instance(zone, name)
                elif "delete" in action:
                    conn.delete_persistent_disk(zone, name)
                else:
                    return "skipped"
            else:
                return "skipped"

            return "success"
            
        except CloudActionError as exc:
            logger.error(f"Cloud API Execution Failed: {exc}")
            return "failed"
        except Exception as exc:
            logger.error(f"Unexpected error executing {action} on {resource_id}: {exc}")
            return "failed"

    def _send_notification(self, message: str) -> None:
        """Mock webhook/Slack notification."""
        logger.info(f"[NOTIFICATION-MOCK] {message}")
        
    def _normalize_action_type(self, action: str) -> str:
        """Normalize generic DB action terms to match allowed policy list strings."""
        action = action.lower()
        if "stop" in action and "ec2" in action: return "stop_ec2"
        if "delete" in action and "ebs" in action: return "delete_ebs"
        if "scale down" in action or "resize" in action: return "scale_down_vm"
        if "delete" in action and "disk" in action: return "delete_disk"
        if "stop" in action and "compute" in action: return "stop_compute"
        return action.replace(" ", "_")

    def _guess_provider(self, service_name: str) -> str:
        svc = service_name.lower()
        if "amazon" in svc or "ec2" in svc or "s3" in svc: return "AWS"
        if "azure" in svc or "vm" in svc: return "Azure"
        if "google" in svc or "gcp" in svc: return "GCP"
        return "AWS"
