def test_forecasting_pipeline_empty(client, setup_default_org):
    # With no history, the forecaster generates naive synthetic data or returns defaults
    resp = client.get("/api/forecast?days=7")
    assert resp.status_code == 200
    data = resp.json()
    # It returns dict with dates and forecasted values
    assert isinstance(data, dict)
    assert "forecast" in data or "predicted_value" in str(data) # weak check, based on schema
