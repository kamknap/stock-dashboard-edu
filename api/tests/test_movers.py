"""Tests for Top movers ranking (pure logic + route, no network)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_market
from app.main import app
from app.models.market import Candles
from app.models.movers import MoverItem
from app.services import movers
from app.services.market_data import ChartData


def chartdata(symbol: str, closes: list[float], currency: str = "USD") -> ChartData:
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    dates = [base + timedelta(days=i) for i in range(len(closes))]
    candles = Candles(
        symbol=symbol,
        currency=currency,
        interval="1d",
        range="6mo",
        dates=dates,
        open=list(closes),
        high=list(closes),
        low=list(closes),
        close=list(closes),
        volume=[100] * len(closes),
    )
    return ChartData(candles=candles, market_price=closes[-1], previous_close=None)


def test_pct_change() -> None:
    assert round(movers.pct_change(110.0, 100.0), 6) == 10.0
    assert round(movers.pct_change(95.0, 100.0), 6) == -5.0
    assert movers.pct_change(100.0, None) is None
    assert movers.pct_change(None, 100.0) is None
    assert movers.pct_change(100.0, 0.0) is None


def test_changes_from_chart() -> None:
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 110.0]
    price, daily, weekly = movers.changes_from_chart(chartdata("X", closes), weekly_sessions=5)
    assert price == 110.0
    assert round(daily, 6) == round((110.0 / 105.0 - 1.0) * 100.0, 6)
    assert round(weekly, 6) == round((110.0 / 101.0 - 1.0) * 100.0, 6)


def test_changes_from_chart_insufficient() -> None:
    price, daily, weekly = movers.changes_from_chart(chartdata("X", [100.0, 110.0]), weekly_sessions=5)
    assert price == 110.0
    assert round(daily, 6) == 10.0
    assert weekly is None  # only 2 candles, need > 5


def test_rank_partitions_by_sign() -> None:
    items = [
        MoverItem(symbol="A", change_pct=10.0),
        MoverItem(symbol="B", change_pct=-5.0),
        MoverItem(symbol="C", change_pct=0.0),
        MoverItem(symbol="D", change_pct=3.0),
        MoverItem(symbol="E", change_pct=-1.0),
    ]
    gainers, losers = movers.rank(items, count=5)
    assert [i.symbol for i in gainers] == ["A", "D"]
    assert [i.symbol for i in losers] == ["B", "E"]
    g1, l1 = movers.rank(items, count=1)
    assert [i.symbol for i in g1] == ["A"]
    assert [i.symbol for i in l1] == ["B"]


class _FakeMarket:
    def __init__(self, charts: dict[str, ChartData]) -> None:
        self._charts = charts

    async def get_charts(self, symbols: list[str]) -> dict[str, ChartData | None]:
        return {s: self._charts.get(s) for s in symbols}


def test_compute_top_movers_ranks_and_skips_missing() -> None:
    charts = {
        "X": chartdata("X", [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 110.0]),  # up
        "Y": chartdata("Y", [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 90.0]),        # down
        "Z": chartdata("Z", [100.0]),                                            # insufficient
    }
    market = _FakeMarket(charts)
    result = asyncio.run(movers.compute_top_movers(market, ["X", "Y", "Z"], count=5))
    assert result.daily.gainers[0].symbol == "X"
    assert result.daily.losers[0].symbol == "Y"
    daily_syms = {m.symbol for m in result.daily.gainers + result.daily.losers}
    assert "Z" not in daily_syms  # only one candle -> no daily change


def test_top_movers_route() -> None:
    charts = {
        "MSFT": chartdata("MSFT", [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 110.0]),
        "NVDA": chartdata("NVDA", [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 90.0]),
    }

    def handler() -> _FakeMarket:
        return _FakeMarket(charts)

    app.dependency_overrides[get_market] = handler
    try:
        client = TestClient(app)
        resp = client.get("/top-movers")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert {m["symbol"] for m in body["daily"]["gainers"]} == {"MSFT"}
    assert {m["symbol"] for m in body["daily"]["losers"]} == {"NVDA"}
    assert "not investment advice" in body["disclaimer"].lower()
