def test_get_autopilot_status(client, admin_headers, setup_default_org):
    resp = client.get(f"/api/autopilot/status?org_id={setup_default_org.id}")
    assert resp.status_code == 200
    assert "enabled" in resp.json()

def test_enable_autopilot(client, admin_headers, setup_default_org):
    resp = client.post(f"/api/autopilot/enable?org_id={setup_default_org.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

def test_disable_autopilot(client, admin_headers, setup_default_org):
    resp = client.post(f"/api/autopilot/disable?org_id={setup_default_org.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

def test_get_autopilot_actions(client, setup_default_org):
    resp = client.get(f"/api/autopilot/actions?org_id={setup_default_org.id}")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_run_autopilot_manually(client, setup_default_org):
    resp = client.post(f"/api/autopilot/run?org_id={setup_default_org.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "actions_executed" in data
    assert "total_savings_estimated" in data
