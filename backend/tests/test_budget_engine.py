def test_empty_budgets(client, admin_headers, setup_default_org):
    resp = client.get(f"/api/budgets?org_id={setup_default_org.id}")
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_budget(client, admin_headers, setup_default_org):
    payload = {
        "org_id": setup_default_org.id,
        "name": "Q1 Overall Budget",
        "monthly_limit": 10000.0,
        "alert_threshold_pct": 0.80
    }
    resp = client.post("/api/budgets", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Q1 Overall Budget"
    assert data["monthly_limit"] == 10000.0

def test_budget_summary(client, admin_headers, setup_default_org):
    # Relies on the previously created budget existing if using the same session
    resp = client.get("/api/budget-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_budget_limit" in data
    assert "total_spent" in data
    
def test_budget_alerts(client, admin_headers):
    resp = client.get("/api/budget-alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
