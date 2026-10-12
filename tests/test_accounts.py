def test_account_retrieval_requires_auth(client):
    response = client.get("/api/accounts/CUST1001")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_account_response_is_masked_and_limited_to_expected_fields(client, auth_headers):
    response = client.get("/api/accounts/CUST1001", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "customer_id": "CUST1001",
        "customer_name": "Rahul Sharma",
        "account_number_masked": "XXXXXX4582",
        "account_type": "Savings",
        "account_status": "ACTIVE",
        "balance": "125000.00",
        "kyc_status": "VERIFIED",
    }
    assert "confirmation_token" not in response.text
    assert "1234567890124582" not in response.text
    assert "test-banking-token" not in response.text


def test_unknown_customer_returns_404(client, auth_headers):
    response = client.get("/api/accounts/UNKNOWN", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


def test_invalid_bearer_token_returns_401(client):
    response = client.get(
        "/api/accounts/CUST1001", headers={"Authorization": "Bearer invalid"}
    )
    assert response.status_code == 401
