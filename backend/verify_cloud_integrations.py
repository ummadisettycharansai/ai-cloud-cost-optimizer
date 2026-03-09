import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_cloud_integrations")

def verify_all():
    logger.info("Starting Phase 4 Backend Verification...")

    # 1. Imports
    logger.info("Step 1: Checking imports...")
    try:
        from cloud_integrations.aws_connector import AWSConnector
        from cloud_integrations.azure_connector import AzureConnector
        from cloud_integrations.gcp_connector import GCPConnector
        from cloud_integrations.credential_manager import CredentialManager, get_credential_manager
        logger.info("✅ Cloud connectors imported successfully.")
    except ImportError as e:
        logger.error(f"❌ Import failed for cloud_integrations: {e}")
        sys.exit(1)

    try:
        from remediation.remediation_engine import RemediationEngine
        logger.info("✅ RemediationEngine imported successfully.")
    except ImportError as e:
        logger.error(f"❌ Import failed for RemediationEngine: {e}")
        sys.exit(1)
        
    try:
        from workers.celery_worker import sync_aws_costs_daily
        logger.info("✅ Celery tasks imported successfully.")
    except ImportError as e:
        logger.error(f"❌ Import failed for celery tasks: {e}")
        sys.exit(1)

    # 2. Credential Manager Initialization
    logger.info("\nStep 2: Checking CredentialManager...")
    try:
        mgr = get_credential_manager()
        test_creds = {"secret": "my-test-password"}
        encrypted = mgr.encrypt(test_creds)
        decrypted = mgr.decrypt(encrypted)
        assert decrypted["secret"] == "my-test-password"
        logger.info("✅ CredentialManager encrypt/decrypt working.")
    except Exception as e:
        logger.error(f"❌ CredentialManager test failed: {e}")
        sys.exit(1)

    # 3. FastAPI App Initialization
    logger.info("\nStep 3: Checking FastAPI app initialization...")
    try:
        from main import app
        # Just importing app forces all routes and models to load
        logger.info("✅ FastAPI app initialized successfully without syntax/import errors.")
    except Exception as e:
        logger.error(f"❌ FastAPI app failed to initialize: {e}")
        sys.exit(1)

    logger.info("\n🎉 Phase 4 Verification Complete! All modules loaded cleanly.")

if __name__ == "__main__":
    verify_all()
