"""Tests for the Yahoo market-data service and routes (no network).

Upstream HTTP is faked with httpx.MockTransport; routes are tested with a
dependency-overridden fake service.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
from fastapi.testclient import TestClient

from app.api.deps import get_market
from app.main import app
from app.models.market import Candles, Snapshot
from app.services.cache import TTLCache
from app.services.market_data import MarketDataError, YahooMarketData

START_TS = 1_700_000_000  # arbitrary fixed epoch for deterministic dates


def make_chart(
    symbol: str = "MSFT",
    currency: str = "USD",
    closes: list[float | None] | None = None,
    market_price: float | None = 105.0,
    previous_close: float | None = 104.0,
) -> dict:
    closes = closes if closes is not None else [100.0, 101.0, None, 103.0, 104.0]
    timestamps = [START_TS + i * 86400 for i in range(len(closes))]
    quote = {
        "open": [None if c is None else c - 0.5 for c in closes],
        "high": [None if c is None else c + 1.0 for c in closes],
        "low": [None if c is None else c - 1.0 for c in closes],
        "close": closes,
        "volume": [None if c is None else 1000 + i for i, c in enumerate(closes)],
    }
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": currency,
                        "symbol": symbol,
                        "regularMarketPrice": market_price,
                        "previousClose": previous_close,
                    },
                    "timestamp": timestamps,
                    "indicators": {"quote": [quote]},
                }
            ],
            "error": None,
        }
    }


def symbol_of(request: httpx.Request) -> str:
    return request.url.path.rsplit("/", 1)[-1]


# ---------- service-layer tests ----------
def test_parse_drops_nulls_and_sets_currency() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_chart())

    async def go() -> Candles:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        svc = YahooMarketData(client, TTLCache(300.0))
        candles = await svc.get_candles("MSFT")
        await client.aclose()
        return candles

    candles = asyncio.run(go())
    # The single None close is dropped: 5 -> 4 usable bars.
    assert candles.size == 4
    assert candles.currency == "USD"
    assert candles.close == [100.0, 101.0, 103.0, 104.0]
    assert all(isinstance(d, datetime) for d in candles.dates)


def test_snapshot_change_is_deterministic() -> None:
    # Daily change uses the prior daily candle (close[-2]), not Yahoo meta.
    closes = [100.0, 101.0, 102.0, 110.0]  # close[-2] = 102.0, close[-1] = 110.0

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_chart(closes=closes, market_price=110.0))

    async def go() -> Snapshot:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        svc = YahooMarketData(client, TTLCache(300.0))
        snap = await svc.get_snapshot("MSFT")
        await client.aclose()
        return snap

    snap = asyncio.run(go())
    assert snap.price == 110.0
    assert snap.previous_close == 102.0
    assert snap.change == 8.0
    assert round(snap.change_pct, 4) == round(8.0 / 102.0 * 100.0, 4)


def test_cache_makes_single_upstream_call() -> None:
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(symbol_of(req))
        return httpx.Response(200, json=make_chart())

    async def go() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        svc = YahooMarketData(client, TTLCache(300.0))
        await svc.get_candles("MSFT")
        await svc.get_snapshot("MSFT")  # same key -> served from cache
        await client.aclose()

    asyncio.run(go())
    assert calls == ["MSFT"]


def test_unknown_symbol_raises() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"chart": {"result": None, "error": "Not Found"}})

    async def go() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        svc = YahooMarketData(client, TTLCache(300.0))
        try:
            await svc.get_snapshot("NOPE")
        finally:
            await client.aclose()

    try:
        asyncio.run(go())
        raised = False
    except MarketDataError:
        raised = True
    assert raised


def test_batch_isolates_failures() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if symbol_of(req) == "BAD":
            return httpx.Response(404, json={"chart": {"result": None, "error": "x"}})
        return httpx.Response(200, json=make_chart(symbol=symbol_of(req)))

    async def go() -> dict[str, Snapshot | None]:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        svc = YahooMarketData(client, TTLCache(300.0))
        out = await svc.get_snapshots(["MSFT", "BAD"])
        await client.aclose()
        return out

    out = asyncio.run(go())
    assert isinstance(out["MSFT"], Snapshot)
    assert out["BAD"] is None


# ---------- route tests (fake service, no network) ----------
class _FakeMarket:
    async def get_snapshot(self, symbol: str, **_: object) -> Snapshot:
        return Snapshot(
            symbol=symbol,
            currency="USD",
            price=105.0,
            previous_close=104.0,
            change=1.0,
            change_pct=0.96,
            as_of=datetime.now(timezone.utc),
        )

    async def get_candles(self, symbol: str, **_: object) -> Candles:
        return Candles(symbol=symbol, currency="USD", interval="1d", range="6mo",
                       close=[1.0, 2.0])


def test_watchlist_route() -> None:
    client = TestClient(app)
    resp = client.get("/watchlist")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 9
    assert {"symbol", "name", "market", "currency"} <= set(body[0])


def test_market_route_ok_for_watchlisted() -> None:
    app.dependency_overrides[get_market] = lambda: _FakeMarket()
    try:
        client = TestClient(app)
        resp = client.get("/market/MSFT")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "MSFT"


def test_market_route_allows_any_valid_symbol() -> None:
    app.dependency_overrides[get_market] = lambda: _FakeMarket()
    try:
        client = TestClient(app)
        resp = client.get("/market/TSLA")  # not in watchlist, but well-formed
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200


def test_market_route_rejects_malformed_symbol() -> None:
    app.dependency_overrides[get_market] = lambda: _FakeMarket()
    try:
        client = TestClient(app)
        resp = client.get("/market/bad!sym")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 404
