"""Tests for daily report assembly and the /run-analysis route (no network)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_llm, get_market, get_store
from app.main import app
from app.models.market import Candles, Snapshot
from app.models.report import LLMNarrative, Source
from app.services.market_data import ChartData
from app.services.store import InMemoryReportStore
from app.services.report import build_daily_report, infer_session


def _candles(symbol: str) -> Candles:
    closes = [100.0 + i for i in range(60)]
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    dates = [base + timedelta(days=i) for i in range(len(closes))]
    return Candles(
        symbol=symbol, currency="USD", interval="1d", range="6mo",
        dates=dates, open=list(closes), high=list(closes), low=list(closes),
        close=list(closes), volume=[100] * len(closes),
    )


class _FakeMarket:
    async def get_candles(self, symbol: str, **_: object) -> Candles:
        return _candles(symbol)

    async def get_snapshot(self, symbol: str, **_: object) -> Snapshot:
        return Snapshot(
            symbol=symbol, currency="USD", price=159.0, previous_close=158.0,
            change=1.0, change_pct=0.63, as_of=datetime.now(timezone.utc),
        )

    async def get_charts(self, symbols: list[str]) -> dict[str, ChartData | None]:
        return {
            s: ChartData(candles=_candles(s), market_price=159.0, previous_close=None)
            for s in symbols
        }


class _FakeLLM:
    async def generate_report_narrative(self, tickers, movers):
        return (
            LLMNarrative(market_summary="summary", ticker_notes={}, risks=["r"]),
            [Source(title="Example", url="https://example.com")],
            True,
        )


def test_infer_session() -> None:
    morning = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
    afternoon = datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)
    assert infer_session(morning) == "morning"
    assert infer_session(afternoon) == "afternoon"


def test_build_daily_report() -> None:
    report = asyncio.run(
        build_daily_report(_FakeMarket(), _FakeLLM(), session="morning", symbols=["MSFT", "NVDA"])
    )
    assert report.session == "morning"
    assert len(report.tickers) == 2
    assert report.llm_ok is True
    assert report.narrative.market_summary == "summary"
    assert report.sources[0].url == "https://example.com"
    assert "not investment advice" in report.disclaimer.lower()
    # indicators were actually computed from the candles
    assert report.tickers[0].indicators.rsi_14 is not None


def test_run_analysis_route_with_secret() -> None:
    app.dependency_overrides[get_market] = lambda: _FakeMarket()
    app.dependency_overrides[get_llm] = lambda: _FakeLLM()
    app.dependency_overrides[get_store] = lambda: InMemoryReportStore()
    try:
        client = TestClient(app)
        resp = client.post(
            "/run-analysis?session=afternoon",
            headers={"X-Scheduler-Secret": "change-me"},
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"] == "afternoon"
    assert body["tickers"]
    assert "market_summary" in body["narrative"]
    assert "not investment advice" in body["disclaimer"].lower()
