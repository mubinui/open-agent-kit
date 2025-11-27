"""Integration tests for Prompts API endpoints."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "prompt_templates.json"
        initial_config = {
            "version": "1.0",
            "contexts": [],
            "fallbacks": {}
        }
        with open(config_path, "w") as f:
            json.dump(initial_config, f)
        
        with patch("src.api.routers.prompts._get_prompts_config_path", return_value=config_path):
            yield tmpdir


def test_create_prompt(client, temp_config_dir):
    """Test creating a new prompt template."""
    prompt_data = {
        "id": "test_prompt",
        "name": "Test Prompt",
        "description": "A test prompt template",
        "template": "Hello {name}, your age is {age}",
        "variables": ["name", "age"],
        "category": "test"
    }
    
    # Note: This will fail without authentication, but tests the endpoint structure
    response = client.post("/api/v1/prompts", json=prompt_data)
    
    # Without auth, we expect 401 or 403
    assert response.status_code in [401, 403]


def test_list_prompts(client, temp_config_dir):
    """Test listing all prompts."""
    # Note: This will fail without authentication
    response = client.get("/api/v1/prompts")
    
    # Without auth, we expect 401 or 403
    assert response.status_code in [401, 403]


def test_get_prompt(client, temp_config_dir):
    """Test getting a specific prompt."""
    # Note: This will fail without authentication
    response = client.get("/api/v1/prompts/test_prompt")
    
    # Without auth, we expect 401 or 403
    assert response.status_code in [401, 403]


def test_update_prompt(client, temp_config_dir):
    """Test updating a prompt template."""
    update_data = {
        "name": "Updated Test Prompt",
        "description": "An updated test prompt"
    }
    
    # Note: This will fail without authentication
    response = client.put("/api/v1/prompts/test_prompt", json=update_data)
    
    # Without auth, we expect 401 or 403
    assert response.status_code in [401, 403]


def test_delete_prompt(client, temp_config_dir):
    """Test deleting a prompt template."""
    # Note: This will fail without authentication
    response = client.delete("/api/v1/prompts/test_prompt")
    
    # Without auth, we expect 401 or 403
    assert response.status_code in [401, 403]


def test_get_prompt_history(client, temp_config_dir):
    """Test getting prompt version history."""
    # Note: This will fail without authentication
    response = client.get("/api/v1/prompts/test_prompt/history")
    
    # Without auth, we expect 401 or 403
    assert response.status_code in [401, 403]
