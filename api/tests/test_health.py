"""Smoke tests for the system and scheduler-protected endpoints."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "environment" in body


def test_root_carries_disclaimer() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "not investment advice" in resp.json()["disclaimer"].lower()


def test_run_analysis_requires_secret() -> None:
    resp = client.post("/run-analysis")
    assert resp.status_code == 401


def test_run_analysis_rejects_wrong_secret() -> None:
    resp = client.post("/run-analysis", headers={"X-Scheduler-Secret": "nope"})
    assert resp.status_code == 401
