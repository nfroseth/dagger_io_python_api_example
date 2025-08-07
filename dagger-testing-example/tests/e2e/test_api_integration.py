"""
Simple e2e test for Hello World API.
Following SIMPLICITY and RELIABILITY principles.
"""

import os

import pytest
import requests


@pytest.fixture
def api_url():
    """Get API URL from environment."""
    return os.environ.get("API_BASE_URL", "http://localhost:8000")


def test_hello_world(api_url):
    """Test that service returns Hello, World!"""
    response = requests.get(api_url, timeout=1)
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}
