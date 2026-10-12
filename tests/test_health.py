import asyncio


def test_health_docs_and_openapi_are_available(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "status": "ok"}
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert "/api/loan-applications/submit" in openapi.json()["paths"]


def test_create_app_is_fastapi_and_seeds_customer(client):
    from app.models.customer import Customer

    assert client.app.title == "Smart Banking Agent"
    with client.app.state.session_factory() as db:
        customer = db.get(Customer, "CUST1001")
        assert customer is not None
        assert customer.customer_name == "Rahul Sharma"


def test_api_refuses_to_start_without_banking_token(tmp_path, monkeypatch):
    import pytest
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "banking_api_token", "")
    app = create_app(f"sqlite:///{(tmp_path / 'missing-token.db').as_posix()}")
    with pytest.raises(RuntimeError, match="BANKING_API_TOKEN must be configured"):
        with TestClient(app):
            pass


def test_confirmation_token_is_redacted_from_access_log_scope():
    from app.main import ConfirmationTokenLogRedaction

    async def endpoint(scope, _receive, _send):
        assert scope["path"] == "/api/loan-applications/secret-token-value/cancel"
        await _send({"type": "http.response.body", "body": b"", "more_body": False})

    async def empty_receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def empty_send(_message):
        assert scope["path"] == "/api/loan-applications/[REDACTED]/cancel"
        return None

    scope = {
        "type": "http",
        "path": "/api/loan-applications/secret-token-value/cancel",
        "raw_path": b"/api/loan-applications/secret-token-value/cancel",
    }
    middleware = ConfirmationTokenLogRedaction(endpoint)
    asyncio.run(middleware(scope, empty_receive, empty_send))
    assert scope["path"] == "/api/loan-applications/[REDACTED]/cancel"
    assert scope["raw_path"] == b"/api/loan-applications/[REDACTED]/cancel"
