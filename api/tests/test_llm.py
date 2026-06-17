"""Tests for the Gemini narrative client (mocked HTTP, no network)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.models.analysis import Indicators, Signal, TickerAnalysis
from app.models.market import Snapshot
from app.models.movers import MoverItem, MoversWindow, TopMovers
from app.services.llm import GeminiClient


def a_ticker(symbol: str = "MSFT") -> TickerAnalysis:
    return TickerAnalysis(
        symbol=symbol,
        name="Microsoft",
        currency="USD",
        snapshot=Snapshot(
            symbol=symbol, currency="USD", price=100.0, previous_close=99.0,
            change=1.0, change_pct=1.01, as_of=datetime.now(timezone.utc),
        ),
        indicators=Indicators(close=100.0, ema_50=95.0, rsi_14=55.0, macd=1.0, macd_signal=0.5),
        signals=[Signal(code="above_ema50", label="Price above EMA50", detail="x", direction="up")],
    )


def some_movers() -> TopMovers:
    item = MoverItem(symbol="MSFT", name="Microsoft", currency="USD", price=100.0, change_pct=1.0)
    return TopMovers(
        as_of=datetime.now(timezone.utc),
        count=5,
        daily=MoversWindow(window="daily", gainers=[item], losers=[]),
        weekly=MoversWindow(window="weekly", gainers=[], losers=[]),
    )


def gemini_response(text: str, chunks: list | None = None) -> dict:
    candidate: dict = {"content": {"parts": [{"text": text}], "role": "model"}}
    if chunks is not None:
        candidate["groundingMetadata"] = {"groundingChunks": chunks}
    return {"candidates": [candidate]}


def run(handler, *, api_key: str = "test-key"):
    async def go():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gem = GeminiClient(client, settings=Settings(gemini_api_key=api_key))
        out = await gem.generate_report_narrative([a_ticker()], some_movers())
        await client.aclose()
        return out

    return asyncio.run(go())


def test_valid_json_and_sources() -> None:
    text = '{"market_summary":"ok summary","ticker_notes":{"MSFT":"note"},"risks":["r1","r2"]}'
    chunks = [{"web": {"uri": "https://example.com/a", "title": "Example"}}]

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=gemini_response(text, chunks))

    narrative, sources, ok = run(handler)
    assert ok is True
    assert narrative.market_summary == "ok summary"
    assert {n.symbol: n.note for n in narrative.ticker_notes}["MSFT"] == "note"
    assert sources[0].url == "https://example.com/a"


def test_json_inside_code_fences() -> None:
    text = '```json\n{"market_summary":"s","ticker_notes":{},"risks":[]}\n```'

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=gemini_response(text, chunks=[]))

    narrative, _, ok = run(handler)
    assert ok is True
    assert narrative.market_summary == "s"


def test_malformed_json_falls_back() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=gemini_response("sorry, no json here"))

    narrative, _, ok = run(handler)
    assert ok is False
    assert narrative.market_summary.startswith("Automated summary")
    assert "MSFT" in {n.symbol for n in narrative.ticker_notes}  # fallback fills notes


def test_http_error_falls_back() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    narrative, sources, ok = run(handler)
    assert ok is False
    assert sources == []
    assert narrative.market_summary.startswith("Automated summary")


def test_missing_api_key_falls_back_without_call() -> None:
    def handler(req: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("should not be called without an API key")

    narrative, sources, ok = run(handler, api_key="")
    assert ok is False
    assert sources == []
    assert narrative.market_summary.startswith("Automated summary")
