"""Smoke tests for the system, chat, and scheduler-protected endpoints."""
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


def test_chat_stub_returns_disclaimer() -> None:
    resp = client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Tell me about AAPL"}]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"]
    assert "not investment advice" in body["disclaimer"].lower()


def test_chat_rejects_empty_messages() -> None:
    resp = client.post("/chat", json={"messages": []})
    assert resp.status_code == 422
