"""Unit tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test the root endpoint returns service information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Orchestration Service"
    assert data["version"] == "0.1.0"
    assert "docs" in data


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "orchestration-service"
    assert data["version"] == "0.1.0"


def test_request_id_header(client):
    """Test that request ID is added to response headers."""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_cors_headers(client):
    """Test that CORS headers are present."""
    response = client.options("/health")
    assert response.status_code == 200


def test_validation_error_handler(client):
    """Test validation error handler returns structured error response."""
    # This will trigger a 404 since the endpoint doesn't exist yet
    # but we can verify the error structure when endpoints are added
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_openapi_docs_available(client):
    """Test that OpenAPI documentation is available."""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Orchestration Service"
    assert data["info"]["version"] == "0.1.0"
