"""Tests for the hand-computed indicators and the analysis route."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi.testclient import TestClient

from app.api.deps import get_market
from app.main import app
from app.models.market import Candles, Snapshot
from app.services import indicators


def candles_from_closes(closes: list[float], symbol: str = "T") -> Candles:
    n = len(closes)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    dates = [base + timedelta(days=i) for i in range(n)]
    return Candles(
        symbol=symbol,
        currency="USD",
        interval="1d",
        range="6mo",
        dates=dates,
        open=list(closes),
        high=list(closes),
        low=list(closes),
        close=list(closes),
        volume=[100] * n,
    )


def test_sma_matches_manual_mean() -> None:
    closes = [float(i) for i in range(1, 61)]  # 1..60
    latest = indicators.compute(candles_from_closes(closes)).latest
    # SMA20 over the last 20 values (41..60) -> mean 50.5
    assert round(latest.sma_20, 4) == 50.5
    assert latest.sma_50 is not None


def test_rsi_extremes() -> None:
    up = indicators.compute(candles_from_closes([float(i) for i in range(1, 40)])).latest
    down = indicators.compute(candles_from_closes([float(i) for i in range(40, 1, -1)])).latest
    assert up.rsi_14 is not None and up.rsi_14 > 99.9
    assert down.rsi_14 is not None and down.rsi_14 < 0.1


def test_insufficient_data_leaves_long_window_none() -> None:
    latest = indicators.compute(candles_from_closes([1.0, 2.0, 3.0, 4.0, 5.0])).latest
    assert latest.sma_50 is None  # needs 50 points
    assert latest.sma_20 is None  # needs 20 points
    assert latest.close == 5.0
    assert latest.as_of is not None


def test_build_context_detects_crosses() -> None:
    idx = pd.to_datetime(["2025-01-01", "2025-01-02"])
    frame = pd.DataFrame(
        {
            "close": [10.0, 11.0],
            "ema_50": [9.0, 9.0],
            "sma_20": [5.0, 7.0],
            "sma_50": [6.0, 6.0],
            "macd": [-1.0, 1.0],
            "macd_signal": [0.0, 0.0],
        },
        index=idx,
    )
    ctx = indicators.build_context(frame)
    assert ctx is not None
    assert ctx.sma_cross_up and ctx.macd_cross_up
    assert not ctx.sma_cross_down and not ctx.macd_cross_down
    assert ctx.close == 11.0


def test_empty_candles_returns_blank_indicators() -> None:
    blank = Candles(symbol="T", currency="USD", interval="1d", range="6mo")
    result = indicators.compute(blank)
    assert result.latest.close is None
    assert indicators.build_context(result.frame) is None


# ---- analysis route (fake market, no network) ----
class _FakeMarket:
    def __init__(self) -> None:
        self._candles = candles_from_closes([float(i) for i in range(1, 60)], "MSFT")
        self._snapshot = Snapshot(
            symbol="MSFT",
            currency="USD",
            price=59.0,
            previous_close=58.0,
            change=1.0,
            change_pct=1.72,
            as_of=datetime.now(timezone.utc),
        )

    async def get_candles(self, symbol: str, **_: object) -> Candles:
        return self._candles

    async def get_snapshot(self, symbol: str, **_: object) -> Snapshot:
        return self._snapshot


def test_analysis_route() -> None:
    app.dependency_overrides[get_market] = lambda: _FakeMarket()
    try:
        client = TestClient(app)
        resp = client.get("/market/MSFT/analysis")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "MSFT"
    assert body["indicators"]["rsi_14"] is not None
    assert isinstance(body["signals"], list)
    assert "not investment advice" in body["disclaimer"].lower()
