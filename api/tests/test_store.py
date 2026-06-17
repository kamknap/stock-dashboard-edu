"""Tests for report persistence (in-memory) and the read endpoints, no network."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_store
from app.config import Settings
from app.main import app
from app.models.movers import MoversWindow, TopMovers
from app.models.report import DailyReport, LLMNarrative
from app.services.store import InMemoryReportStore, create_report_store


def a_report(date: str = "2026-06-17", session: str = "morning", when=None) -> DailyReport:
    when = when or datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)
    return DailyReport(
        date=date,
        session=session,  # type: ignore[arg-type]
        generated_at=when,
        tickers=[],
        top_movers=TopMovers(
            as_of=when, count=5,
            daily=MoversWindow(window="daily", gainers=[], losers=[]),
            weekly=MoversWindow(window="weekly", gainers=[], losers=[]),
        ),
        narrative=LLMNarrative(market_summary="s"),
    )


def test_in_memory_round_trip() -> None:
    async def go():
        store = InMemoryReportStore()
        assert await store.latest() is None
        await store.save(a_report())
        got = await store.get("2026-06-17", "morning")
        assert got is not None and got.date == "2026-06-17"
        assert await store.get("2026-06-17", "afternoon") is None
        return await store.latest()

    latest = asyncio.run(go())
    assert latest is not None and latest.session == "morning"


def test_latest_picks_newer() -> None:
    async def go():
        store = InMemoryReportStore()
        await store.save(a_report(session="morning", when=datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)))
        await store.save(a_report(session="afternoon", when=datetime(2026, 6, 17, 15, 0, tzinfo=timezone.utc)))
        return await store.latest()

    latest = asyncio.run(go())
    assert latest is not None and latest.session == "afternoon"


def test_factory_falls_back_to_memory_when_unconfigured() -> None:
    store = create_report_store(Settings(gcp_project_id="", google_application_credentials=""))
    assert isinstance(store, InMemoryReportStore)


def test_report_routes() -> None:
    store = InMemoryReportStore()
    app.dependency_overrides[get_store] = lambda: store
    try:
        client = TestClient(app)
        assert client.get("/reports/latest").status_code == 404
        asyncio.run(store.save(a_report()))
        latest = client.get("/reports/latest")
        assert latest.status_code == 200 and latest.json()["date"] == "2026-06-17"
        assert client.get("/reports/2026-06-17/morning").status_code == 200
        assert client.get("/reports/2026-06-17/afternoon").status_code == 404
        assert client.get("/reports/2026-06-17/midnight").status_code == 422
    finally:
        app.dependency_overrides.clear()
