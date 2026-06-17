"""Tests for the chat agent (ticker resolution + grounded reply), no network."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_llm, get_market
from app.main import app
from app.models.market import Candles, Snapshot
from app.models.schemas import ChatMessage, ChatRequest, ChatRole, Source
from app.services import chat


# ---- ticker resolution ----
def test_resolve_symbol() -> None:
    assert chat.resolve_symbol("what about Nvidia today?") == "NVDA"
    assert chat.resolve_symbol("tell me about KGHM") == "KGH.WA"
    assert chat.resolve_symbol("MSFT?") == "MSFT"
    assert chat.resolve_symbol("how is samsung doing") == "005930.KS"
    assert chat.resolve_symbol("thoughts on google") == "GOOGL"
    assert chat.resolve_symbol("just chatting about the weather") is None


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


class _FakeLLM:
    def __init__(self, ok: bool = True) -> None:
        self._ok = ok
        self.last_contents: list[dict] | None = None

    async def generate_chat_reply(self, contents, system_instruction):
        self.last_contents = contents
        if not self._ok:
            return "", [], False
        return (
            "Trend is up; RSI elevated; recent news positive. "
            "Educational tool, not investment advice.",
            [Source(title="Example", url="https://example.com")],
            True,
        )


def _request(text: str) -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role=ChatRole.user, content=text)])


def test_answer_chat_with_ticker_injects_data() -> None:
    llm = _FakeLLM(ok=True)
    resp = asyncio.run(chat.answer_chat(_FakeMarket(), llm, _request("How is NVDA doing?")))
    assert resp.ticker == "NVDA"
    assert resp.sources[0].url == "https://example.com"
    assert "not investment advice" in resp.disclaimer.lower()
    # the deterministic data block was appended to the last user turn
    joined = " ".join(p["text"] for p in llm.last_contents[-1]["parts"])
    assert "Reference data for NVDA" in joined


def test_answer_chat_fallback_when_llm_down() -> None:
    resp = asyncio.run(chat.answer_chat(_FakeMarket(), _FakeLLM(ok=False), _request("NVDA?")))
    assert resp.ticker == "NVDA"
    assert resp.sources == []
    assert "not investment advice" in resp.reply.lower()


def test_chat_route() -> None:
    app.dependency_overrides[get_market] = lambda: _FakeMarket()
    app.dependency_overrides[get_llm] = lambda: _FakeLLM(ok=True)
    try:
        client = TestClient(app)
        resp = client.post("/chat", json={"messages": [{"role": "user", "content": "Tell me about MSFT"}]})
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "MSFT"
    assert body["reply"]
    assert "not investment advice" in body["disclaimer"].lower()


def test_chat_route_rejects_empty_messages() -> None:
    app.dependency_overrides[get_market] = lambda: _FakeMarket()
    app.dependency_overrides[get_llm] = lambda: _FakeLLM(ok=True)
    try:
        client = TestClient(app)
        resp = client.post("/chat", json={"messages": []})
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 422
