import sys
sys.path.insert(0, '.')

print("Testing models...", end=" ")
from models import AutopilotPolicy, AutopilotAction
print("OK")

print("Testing schemas...", end=" ")
from schemas import AutopilotPolicyOut, AutopilotActionOut, AutopilotRunResult
print("OK")

print("Testing crud...", end=" ")
from crud import (get_autopilot_policy, enable_autopilot, disable_autopilot,
                  log_autopilot_action, get_autopilot_actions, get_daily_action_count)
print("OK")

print("Testing remediation engine...", end=" ")
from remediation.remediation_engine import RemediationEngine
print("OK")

print("Testing database setup...", end=" ")
from database import engine, SessionLocal
from models import Base
Base.metadata.create_all(bind=engine)
print("OK")

print("Testing CRUD with live DB...", end=" ")
db = SessionLocal()
policy = get_autopilot_policy(db, org_id=99)
print(f"OK (policy enabled={policy.enabled}, daily_limit={policy.max_daily_actions})")

# Test enable/disable
enabled = enable_autopilot(db, org_id=99)
assert enabled.enabled == True, "Enable failed"
disabled = disable_autopilot(db, org_id=99)
assert disabled.enabled == False, "Disable failed"
print("enable/disable toggle: OK")

# Test action logging
action = log_autopilot_action(db, {
    "org_id": 99, "provider": "AWS", "resource_id": "i-test123",
    "action": "stop_ec2", "status": "success", "estimated_savings": 45.50
})
assert action.id is not None
print(f"Action logging: OK (id={action.id})")

count = get_daily_action_count(db, org_id=99)
print(f"Daily action count: {count}")

actions = get_autopilot_actions(db, org_id=99, limit=10)
print(f"Action retrieval: OK ({len(actions)} actions found)")
db.close()

print()
print("=" * 50)
print("ALL AUTOPILOT MODULE CHECKS PASSED")
print("=" * 50)
