def test_list_cloud_accounts_empty(client, admin_headers, setup_default_org):
    response = client.get(f"/api/cloud/accounts?org_id={setup_default_org.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []

def test_connect_aws_account(client, admin_headers, setup_default_org):
    payload = {
        "org_id": setup_default_org.id,
        "provider": "aws",
        "account_alias": "AWS-Prod",
        "region": "us-east-1",
        "access_key": "AKIA-MOCK",
        "secret_key": "MOCK-SECRET"
    }
    response = client.post("/api/connect/aws", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "aws"
    assert data["account_alias"] == "AWS-Prod"
    # Ensure credential blob is not leaked
    assert "access_key" not in data

def test_delete_cloud_account(client, admin_headers, setup_default_org):
    # Setup
    payload = {
        "org_id": setup_default_org.id,
        "provider": "aws",
        "account_alias": "AWS-Prod",
        "region": "us-east-1",
    }
    create_resp = client.post("/api/connect/aws", json=payload, headers=admin_headers)
    acct_id = create_resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/api/cloud/accounts/{acct_id}", headers=admin_headers)
    assert del_resp.status_code == 204

    # Verify deleted
    list_resp = client.get(f"/api/cloud/accounts?org_id={setup_default_org.id}", headers=admin_headers)
    assert len(list_resp.json()) == 0

def test_sync_cloud_account(client, admin_headers, setup_default_org):
    # Setup
    payload = {
        "org_id": setup_default_org.id,
        "provider": "aws",
        "account_alias": "AWS-Prod",
        "region": "us-east-1",
    }
    create_resp = client.post("/api/connect/aws", json=payload, headers=admin_headers)
    acct_id = create_resp.json()["id"]

    # Sync
    sync_resp = client.post(f"/api/cloud/accounts/{acct_id}/sync", headers=admin_headers)
    assert sync_resp.status_code == 200
    assert "successfully" in sync_resp.json()["message"]
