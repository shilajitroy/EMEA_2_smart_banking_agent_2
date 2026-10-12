from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "banking_api_token", "test-banking-token")
    app = create_app(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-banking-token"}
