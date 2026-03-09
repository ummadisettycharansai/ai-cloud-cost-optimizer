"""
Cloud Integrations Package

Provides real cloud provider connectors for:
  - AWS (boto3 / IAM role assumption)
  - Azure (Service Principal / azure-identity)
  - GCP (Service Account JSON / ADC)

Also includes CredentialManager for secure encrypted storage of cloud credentials.
"""
from .credential_manager import CredentialManager  # noqa: F401
from .aws_connector import AWSConnector  # noqa: F401
from .azure_connector import AzureConnector  # noqa: F401
from .gcp_connector import GCPConnector  # noqa: F401

__all__ = ["CredentialManager", "AWSConnector", "AzureConnector", "GCPConnector"]
