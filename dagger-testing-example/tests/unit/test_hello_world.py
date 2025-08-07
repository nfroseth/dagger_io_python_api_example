"""
Unit tests for hello world FastAPI application.
Following Test Architect principles:
- Test isolation with no global state dependencies
- Focus on business logic correctness
- Strategic mocking at interface boundaries only
- Comprehensive assertions validating actual behavior
"""

import pytest
from fastapi.testclient import TestClient

from src.hello_world import app


@pytest.fixture
def client():
    """
    Create isolated test client for each test.
    Ensures no test interdependencies.
    """
    return TestClient(app)


class TestRootEndpoint:
    """Test suite for root endpoint following FIRST principles."""

    def test_root_returns_success_status(self, client):
        """Verify root endpoint returns 200 OK status."""
        response = client.get("/")

        assert response.status_code == 200

    def test_root_returns_hello_world_message(self, client):
        """Verify root endpoint returns correct message structure."""
        response = client.get("/")

        # Validate response structure
        assert response.json() == {"message": "Hello, World!"}

        # Validate content type
        assert response.headers["content-type"] == "application/json"

    def test_root_response_is_json(self, client):
        """Verify response is valid JSON."""
        response = client.get("/")

        # This will raise if not valid JSON
        json_data = response.json()
        assert isinstance(json_data, dict)
        assert "message" in json_data


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_returns_success_status(self, client):
        """Verify health endpoint returns 200 OK status."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Verify health endpoint returns correct health status."""
        response = client.get("/health")

        json_data = response.json()
        assert json_data["status"] == "healthy"
        assert json_data["service"] == "hello-world"

    def test_health_response_structure(self, client):
        """Verify health response has all required fields."""
        response = client.get("/health")

        json_data = response.json()
        required_fields = {"status", "service"}
        assert set(json_data.keys()) == required_fields


class TestErrorHandling:
    """Test error scenarios and edge cases."""

    def test_nonexistent_endpoint_returns_404(self, client):
        """Verify proper 404 handling for undefined routes."""
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_invalid_method_returns_405(self, client):
        """Verify proper method not allowed handling."""
        response = client.post("/")

        assert response.status_code == 405
