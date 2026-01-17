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
    """Test the goodbye endpoint with default behavior."""
    response = client.get("/goodbye")
    assert response.status_code == 200
    data = response.json()
    assert data == {"message": "Goodbye, World!"}


def test_goodbye_endpoint_with_name():
    """Test the goodbye endpoint with a custom name parameter."""
    response = client.get("/goodbye?name=Alice")
    assert response.status_code == 200
    data = response.json()
    assert data == {"message": "Goodbye, Alice!"}


def test_goodbye_endpoint_with_encoded_name():
    """Test the goodbye endpoint with URL-encoded name."""
    response = client.get("/goodbye?name=John%20Doe")
    assert response.status_code == 200
    data = response.json()
    assert data == {"message": "Goodbye, John Doe!"}
