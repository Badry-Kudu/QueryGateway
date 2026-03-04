"""Health endpoint smoke tests."""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/admin/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
