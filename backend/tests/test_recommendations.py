def test_generate_recommendations(client):
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    
def test_savings_opportunities(client):
    resp = client.get("/api/savings-opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert "potential_savings" in data
    assert "recommendations" in data
    assert isinstance(data["potential_savings"], float)

def test_cost_efficiency_scoring(client):
    resp = client.get("/api/cost-efficiency")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_waste_candidates" in data
    assert "all_resources" in data
    assert "summary" in data

def test_rightsizing_recommendations(client):
    resp = client.get("/api/rightsizing")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
