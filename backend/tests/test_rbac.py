def test_admin_can_create_org(client, admin_headers):
    payload = {
        "name": "Admin Org",
        "slug": "admin-org",
        "plan": "premium"
    }
    resp = client.post("/api/organizations", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "Admin Org"

def test_viewer_cannot_create_org(client, viewer_headers):
    payload = {
        "name": "Viewer Org",
        "slug": "viewer-org",
        "plan": "free"
    }
    resp = client.post("/api/organizations", json=payload, headers=viewer_headers)
    assert resp.status_code == 403

def test_viewer_cannot_enable_autopilot(client, viewer_headers, setup_default_org):
    resp = client.post(f"/api/autopilot/enable?org_id={setup_default_org.id}", headers=viewer_headers)
    assert resp.status_code == 403

def test_viewer_cannot_modify_budgets(client, viewer_headers, setup_default_org):
    payload = {
        "org_id": setup_default_org.id,
        "name": "Hacked Budget",
        "monthly_amount": 99999.0,
        "alert_threshold_percent": 50.0
    }
    resp = client.post("/api/budgets", json=payload, headers=viewer_headers)
    assert resp.status_code == 403

    # But viewer can list budgets
    list_resp = client.get(f"/api/budgets?org_id={setup_default_org.id}", headers=viewer_headers)
    assert list_resp.status_code == 200
