"""Tests for the FastAPI application endpoints."""

import pytest
from fastapi.testclient import TestClient

from aidw.server.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_hello_endpoint_success(client):
    """Test that /hello endpoint returns successful response."""
    response = client.get("/hello")
    assert response.status_code == 200


def test_hello_endpoint_status_code(client):
    """Test that /hello endpoint returns 200 OK status."""
    response = client.get("/hello")
    assert response.status_code == 200


def test_hello_response_structure(client):
    """Test that /hello response has correct JSON structure with 'message' key."""
    response = client.get("/hello")
    data = response.json()
    assert "message" in data
    assert isinstance(data["message"], str)


def test_hello_response_content(client):
    """Test that /hello message content is 'Hello, World!'."""
    response = client.get("/hello")
    data = response.json()
    assert data["message"] == "Hello, World!"


def test_hello_endpoint_post_method_not_allowed(client):
    """Test that POST request to /hello returns 405 Method Not Allowed."""
    response = client.post("/hello")
    assert response.status_code == 405


def test_hello_endpoint_put_method_not_allowed(client):
    """Test that PUT request to /hello returns 405 Method Not Allowed."""
    response = client.put("/hello")
    assert response.status_code == 405


def test_hello_endpoint_delete_method_not_allowed(client):
    """Test that DELETE request to /hello returns 405 Method Not Allowed."""
    response = client.delete("/hello")
    assert response.status_code == 405


def test_hello_with_query_params(client):
    """Test that /hello handles unexpected query parameters gracefully."""
    response = client.get("/hello?foo=bar&baz=qux")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello, World!"


def test_hello_response_content_type(client):
    """Test that /hello response Content-Type is application/json."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
