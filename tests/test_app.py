"""Tests for FastAPI application endpoints."""

from fastapi.testclient import TestClient

from aidw.server.app import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_goodbye_endpoint():
    """Test the goodbye endpoint."""
    response = client.get("/goodbye")
    assert response.status_code == 200
    data = response.json()
    assert data == {"message": "Goodbye, World!"}
