"""Regression tests for the CrewAI upgrade API surface."""

from fastapi.testclient import TestClient

from src.api.app_factory import create_app
from src.config.settings import reset_settings


def test_crewai_config_round_trip(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CREWAI_STORAGE_DIR", str(tmp_path / "crewai"))
    reset_settings()
    client = TestClient(create_app())

    response = client.get("/api/v1/crewai/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"] == "crewai"

    payload["process"] = "hierarchical"
    payload["memory"]["retention"] = "long_term"
    payload["deployment"]["auth_mode"] = "keycloak"

    saved = client.put("/api/v1/crewai/config", json=payload)
    assert saved.status_code == 200
    assert saved.json()["process"] == "hierarchical"

    reloaded = client.get("/api/v1/crewai/config")
    assert reloaded.status_code == 200
    assert reloaded.json()["memory"]["retention"] == "long_term"
    assert reloaded.json()["deployment"]["auth_mode"] == "keycloak"

    reset_settings()


def test_workflow_execute_dry_run_uses_crewai_validation(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CREWAI_STORAGE_DIR", str(tmp_path / "crewai"))
    reset_settings()
    client = TestClient(create_app())

    workflows = client.get("/api/v1/workflows")
    assert workflows.status_code == 200
    workflow_id = workflows.json()[0]["id"]

    response = client.post(
        f"/api/v1/workflows/{workflow_id}/execute",
        json={"message": "validate this crew", "dry_run": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["metadata"]["runtime"] == "crewai"
    assert payload["metadata"]["validated"] is True

    reset_settings()
