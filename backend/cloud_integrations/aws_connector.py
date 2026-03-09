"""
AWS Cloud Connector — Real AWS SDK integration using boto3.

Supports authentication via:
  1. IAM Role ARN assumption (via STS AssumeRole) — recommended for cross-account access
  2. Static Access Key + Secret Key
  3. Default credential chain (env vars, ~/.aws, instance profile)

Implements:
  - Cost Explorer: get_cost_by_service(), get_cost_by_region()
  - EC2 Remediation: stop_ec2_instance(), describe_instance()
  - EBS Remediation: delete_ebs_volume(), list_unattached_volumes()
  - S3 Optimization: move_s3_to_glacier()
  - Resource Inventory: list_ec2_instances(), list_ebs_volumes()

All remediation methods perform a pre-flight safety check (state validation)
before executing irreversible actions.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional

from .credential_manager import CloudActionError

logger = logging.getLogger(__name__)

try:
    import boto3  # pyre-ignore[21]
    from botocore.exceptions import ClientError, NoCredentialsError  # pyre-ignore[21]
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None  # type: ignore


class AWSConnector:
    """
    Real AWS integration via boto3.
    Instantiate with role_arn (cross-account) or access_key+secret_key (direct).
    Falls back to mock data / graceful error when credentials are absent.
    """

    def __init__(
        self,
        role_arn: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
        external_id: Optional[str] = None,
    ) -> None:
        self.region = region
        self._session: Optional[Any] = None
        self._account_id: Optional[str] = None
        self.is_connected = False

        if not BOTO3_AVAILABLE:
            logger.warning("AWSConnector: boto3 not installed — operating in offline mode.")
            return

        try:
            if role_arn:
                # STS AssumeRole — preferred for multi-account FinOps
                base_session = boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region,
                )
                sts = base_session.client("sts")
                assume_kwargs: Dict[str, Any] = {
                    "RoleArn": role_arn,
                    "RoleSessionName": "FinOpsAutopilot",
                    "DurationSeconds": 3600,
                }
                if external_id:
                    assume_kwargs["ExternalId"] = external_id

                creds = sts.assume_role(**assume_kwargs)["Credentials"]
                self._session = boto3.Session(
                    aws_access_key_id=creds["AccessKeyId"],
                    aws_secret_access_key=creds["SecretAccessKey"],
                    aws_session_token=creds["SessionToken"],
                    region_name=region,
                )
                logger.info(f"AWSConnector: Assumed role {role_arn}")
            elif access_key and secret_key:
                self._session = boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region,
                )
                logger.info("AWSConnector: Using static credentials.")
            else:
                # Default chain: env vars, ~/.aws/credentials, EC2 instance profile
                self._session = boto3.Session(region_name=region)
                logger.info("AWSConnector: Using default credential chain.")

            # Verify connectivity
            sts_check = self._session.client("sts")
            identity = sts_check.get_caller_identity()
            self._account_id = identity.get("Account")
            self.is_connected = True
            logger.info(f"AWSConnector: Connected — Account {self._account_id}")

        except (NoCredentialsError, ClientError, Exception) as exc:
            logger.warning(f"AWSConnector: Authentication failed ({exc}). Connector offline.")

    # ─────────────────────────────────────────────────────────────────────────
    # Cost Data
    # ─────────────────────────────────────────────────────────────────────────

    def get_cost_by_service(self, days: int = 30) -> List[Dict[str, Any]]:
        """Daily cost breakdown grouped by AWS SERVICE dimension."""
        if not self.is_connected or not self._session:
            return []

        end = datetime.date.today()
        start = end - datetime.timedelta(days=days)
        ce = self._session.client("ce", region_name="us-east-1")

        try:
            resp = ce.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(end)},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            results = []
            for period in resp.get("ResultsByTime", []):
                date_str = period["TimePeriod"]["Start"]
                for group in period.get("Groups", []):
                    service = group["Keys"][0]
                    cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    if cost > 0:
                        results.append({
                            "date": date_str,
                            "service": service,
                            "cost": round(cost, 4),
                            "provider": "AWS",
                            "account_id": self._account_id,
                        })
            return results
        except ClientError as exc:
            raise CloudActionError(f"AWS Cost Explorer error: {exc}") from exc

    def get_cost_by_region(self, days: int = 30) -> List[Dict[str, Any]]:
        """Daily cost breakdown grouped by AWS REGION dimension."""
        if not self.is_connected or not self._session:
            return []

        end = datetime.date.today()
        start = end - datetime.timedelta(days=days)
        ce = self._session.client("ce", region_name="us-east-1")

        try:
            resp = ce.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(end)},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "REGION"}],
            )
            results = []
            for period in resp.get("ResultsByTime", []):
                date_str = period["TimePeriod"]["Start"]
                for group in period.get("Groups", []):
                    region = group["Keys"][0]
                    cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    if cost > 0:
                        results.append({
                            "date": date_str,
                            "region": region,
                            "cost": round(cost, 4),
                            "provider": "AWS",
                            "account_id": self._account_id,
                        })
            return results
        except ClientError as exc:
            raise CloudActionError(f"AWS Cost by Region error: {exc}") from exc

    # ─────────────────────────────────────────────────────────────────────────
    # Resource Inventory
    # ─────────────────────────────────────────────────────────────────────────

    def list_ec2_instances(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all EC2 instances with state and basic metadata."""
        if not self.is_connected or not self._session:
            return []
        r = region or self.region
        ec2 = self._session.client("ec2", region_name=r)
        try:
            resp = ec2.describe_instances()
            instances = []
            for reservation in resp.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                    instances.append({
                        "instance_id": inst["InstanceId"],
                        "instance_type": inst.get("InstanceType"),
                        "state": inst["State"]["Name"],
                        "region": r,
                        "name": tags.get("Name", inst["InstanceId"]),
                        "launch_time": str(inst.get("LaunchTime", "")),
                        "provider": "AWS",
                    })
            return instances
        except ClientError as exc:
            logger.error(f"AWSConnector.list_ec2_instances: {exc}")
            return []

    def describe_instance(self, instance_id: str, region: Optional[str] = None) -> Dict[str, Any]:
        """Get state and metadata for a single EC2 instance."""
        if not self.is_connected or not self._session:
            raise CloudActionError("AWSConnector not connected.")
        r = region or self.region
        ec2 = self._session.client("ec2", region_name=r)
        try:
            resp = ec2.describe_instances(InstanceIds=[instance_id])
            for reservation in resp.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    return {
                        "instance_id": inst["InstanceId"],
                        "state": inst["State"]["Name"],
                        "instance_type": inst.get("InstanceType"),
                        "region": r,
                    }
            raise CloudActionError(f"Instance {instance_id} not found.")
        except ClientError as exc:
            raise CloudActionError(f"describe_instance failed: {exc}") from exc

    def list_unattached_volumes(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """List EBS volumes with state=available (not attached to any instance)."""
        if not self.is_connected or not self._session:
            return []
        r = region or self.region
        ec2 = self._session.client("ec2", region_name=r)
        try:
            resp = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])
            volumes = []
            for vol in resp.get("Volumes", []):
                volumes.append({
                    "volume_id": vol["VolumeId"],
                    "size_gb": vol.get("Size"),
                    "volume_type": vol.get("VolumeType"),
                    "state": vol["State"],
                    "region": r,
                    "provider": "AWS",
                })
            return volumes
        except ClientError as exc:
            logger.error(f"AWSConnector.list_unattached_volumes: {exc}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Remediation Actions
    # ─────────────────────────────────────────────────────────────────────────

    def stop_ec2_instance(self, instance_id: str, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Stop an EC2 instance.
        Pre-flight: verifies instance is in 'running' state before stopping.
        Returns: {"instance_id", "previous_state", "current_state", "action"}
        Raises: CloudActionError on failure or invalid state.
        """
        if not self.is_connected or not self._session:
            raise CloudActionError("AWSConnector not connected — cannot stop instance.")

        r = region or self.region
        info = self.describe_instance(instance_id, r)

        if info["state"] not in ("running", "pending"):
            raise CloudActionError(
                f"stop_ec2_instance: Instance {instance_id} is '{info['state']}', not running. No action taken."
            )

        ec2 = self._session.client("ec2", region_name=r)
        try:
            resp = ec2.stop_instances(InstanceIds=[instance_id])
            change = resp["StoppingInstances"][0]
            result = {
                "action": "stop_ec2",
                "instance_id": instance_id,
                "previous_state": change["PreviousState"]["Name"],
                "current_state": change["CurrentState"]["Name"],
                "region": r,
                "provider": "AWS",
            }
            logger.info(f"[AWSConnector] Stopped EC2 {instance_id}: {result}")
            return result
        except ClientError as exc:
            raise CloudActionError(f"stop_ec2_instance failed: {exc}") from exc

    def delete_ebs_volume(self, volume_id: str, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete an EBS volume.
        Pre-flight: only deletes volumes in 'available' (unattached) state.
        Raises: CloudActionError if volume is attached or operation fails.
        """
        if not self.is_connected or not self._session:
            raise CloudActionError("AWSConnector not connected — cannot delete volume.")

        r = region or self.region
        ec2 = self._session.client("ec2", region_name=r)

        # Pre-flight check — refuse to delete attached volumes
        try:
            resp = ec2.describe_volumes(VolumeIds=[volume_id])
            vol = resp["Volumes"][0]
            if vol["State"] != "available":
                raise CloudActionError(
                    f"delete_ebs_volume: Volume {volume_id} is in state '{vol['State']}'"
                    " (not 'available'). Will not delete attached volume."
                )
        except ClientError as exc:
            raise CloudActionError(f"Volume pre-flight check failed: {exc}") from exc

        try:
            ec2.delete_volume(VolumeId=volume_id)
            result = {
                "action": "delete_ebs",
                "volume_id": volume_id,
                "region": r,
                "provider": "AWS",
                "status": "deleted",
            }
            logger.info(f"[AWSConnector] Deleted EBS volume {volume_id}")
            return result
        except ClientError as exc:
            raise CloudActionError(f"delete_ebs_volume failed: {exc}") from exc

    def move_s3_to_glacier(self, bucket: str, prefix: str = "") -> Dict[str, Any]:
        """
        Apply an S3 Lifecycle rule to transition objects to Glacier after 0 days.
        This is non-destructive — objects remain accessible but storage class changes.
        """
        if not self.is_connected or not self._session:
            raise CloudActionError("AWSConnector not connected — cannot apply S3 lifecycle.")

        s3 = self._session.client("s3")
        rule_id = f"finops-glacier-{prefix.replace('/', '-') or 'all'}"

        lifecycle_config = {
            "Rules": [
                {
                    "ID": rule_id,
                    "Status": "Enabled",
                    "Filter": {"Prefix": prefix},
                    "Transitions": [
                        {"Days": 0, "StorageClass": "GLACIER"},
                    ],
                    "NoncurrentVersionTransitions": [
                        {"NoncurrentDays": 30, "StorageClass": "GLACIER"},
                    ],
                }
            ]
        }

        try:
            s3.put_bucket_lifecycle_configuration(
                Bucket=bucket,
                LifecycleConfiguration=lifecycle_config,
            )
            result = {
                "action": "move_s3_glacier",
                "bucket": bucket,
                "prefix": prefix or "(all objects)",
                "rule_id": rule_id,
                "provider": "AWS",
                "status": "lifecycle_applied",
            }
            logger.info(f"[AWSConnector] Applied Glacier lifecycle to s3://{bucket}/{prefix}")
            return result
        except ClientError as exc:
            raise CloudActionError(f"move_s3_to_glacier failed: {exc}") from exc
