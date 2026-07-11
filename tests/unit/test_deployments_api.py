"""Unit tests for flash deployment lifecycle APIs (same-origin, no subprocesses)."""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers import deployments as deployments_router


@pytest.fixture
def client(tmp_path, monkeypatch):
    config_path = tmp_path / "deployments.json"
    deployments_dir = tmp_path / "deployments"

    monkeypatch.setattr(deployments_router, "CONFIG_PATH", config_path)
    monkeypatch.setattr(deployments_router, "DEPLOYMENTS_DIR", deployments_dir)

    app = FastAPI()
    app.include_router(deployments_router.router)
    app.include_router(deployments_router.pages_router)

    with TestClient(app) as test_client:
        yield test_client


def test_flash_deploy_writes_page_and_serves_it(client, tmp_path):
    payload = {
        "workflow_id": "demo_multi_agent",
        "name": "demo-chatbot",
        "title": "Demo Chatbot",
    }

    create_response = client.post("/api/v1/deployments/flash", json=payload)
    assert create_response.status_code == 201
    deployment = create_response.json()
    assert deployment["status"] == "active"
    assert deployment["url"] == "/d/demo-chatbot/"

    # The generated page exists on disk and is served same-origin
    index_path = Path(deployment["path"]) / "index.html"
    assert index_path.exists()
    page = client.get(f"/d/{deployment['id']}/")
    assert page.status_code == 200
    assert "Demo Chatbot" in page.text
    # Generated page must not hardcode a host — same-origin API calls only
    assert "127.0.0.1" not in page.text
    assert "localhost" not in page.text


def test_list_and_delete_deployment(client, tmp_path):
    payload = {"workflow_id": "demo_multi_agent", "name": "demo-chatbot"}
    created = client.post("/api/v1/deployments/flash", json=payload).json()

    listing = client.get("/api/v1/deployments")
    assert listing.status_code == 200
    assert [d["id"] for d in listing.json()] == [created["id"]]

    delete_response = client.delete(f"/api/v1/deployments/{created['id']}")
    assert delete_response.status_code == 204

    config = json.loads((tmp_path / "deployments.json").read_text(encoding="utf-8"))
    assert config["deployments"] == []
    assert not Path(created["path"]).exists()
    assert client.get(f"/d/{created['id']}/").status_code == 404


def test_delete_missing_deployment_returns_404(client):
    assert client.delete("/api/v1/deployments/nope").status_code == 404


def test_preview_reports_url_and_path(client):
    payload = {"workflow_id": "demo_multi_agent", "name": "My Bot!"}
    response = client.post("/api/v1/deployments/preview", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "/d/my-bot/"
    assert body["warnings"] == []


def test_flash_deploy_replaces_existing_record(client):
    payload = {"workflow_id": "demo_multi_agent", "name": "demo-chatbot"}
    client.post("/api/v1/deployments/flash", json=payload)
    client.post("/api/v1/deployments/flash", json=payload)

    listing = client.get("/api/v1/deployments").json()
    assert len(listing) == 1
