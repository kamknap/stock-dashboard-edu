"""Analytical chat agent (option A: we resolve the ticker, then ground once).

Function-calling + Google Search grounding cannot be combined in one request on
Gemini 2.5, so instead of letting the model invoke a tool we resolve the ticker
from the user's message ourselves, fetch the deterministic data via the shared
analysis layer (our get_stock_data), inject it as the source of truth, and make
a single grounded Gemini call for the news/context narrative. The answer never
gives a buy/sell verdict and always carries the disclaimer.
"""
from __future__ import annotations

import re

from app.models.schemas import DISCLAIMER, ChatRequest, ChatResponse, ChatRole
from app.services.analysis import analyze_symbol
from app.services.llm import GeminiClient
from app.services.market_data import MarketDataError, YahooMarketData
from app.models.analysis import TickerAnalysis
from app.watchlist import DEFAULT_WATCHLIST

CHAT_SYSTEM = (
    "You are an EDUCATIONAL stock-market assistant. If reference data for a "
    "ticker is provided, it was computed deterministically and is the source of "
    "truth — never recompute or contradict it. Use Google Search for fresh, "
    "relevant news. Answer concisely and cover: current trend, key indicators, "
    "fresh news, and risks. Do NOT give buy/sell/hold advice and do NOT predict "
    "prices. Always answer in the same language as the user's last message. End "
    "your answer with: 'Educational tool, not investment advice.' "
    "Use plain punctuation and do not use em dashes; prefer commas or periods. "
    "Write in plain prose: no markdown, no asterisks, bold, headings or bullet symbols."
)


def _build_aliases() -> dict[str, str]:
    """Map a lowercase brand word to a watchlist symbol (first name token)."""
    aliases: dict[str, str] = {}
    for w in DEFAULT_WATCHLIST:
        first = re.findall(r"[a-z0-9]+", w.name.lower())
        if first:
            aliases.setdefault(first[0], w.symbol)
    aliases.update({"google": "GOOGL", "alphabet": "GOOGL"})
    return aliases


_ALIASES = _build_aliases()


def resolve_symbol(text: str) -> str | None:
    """Best-effort watchlist ticker from free text (symbol substring or brand)."""
    low = text.lower()
    for w in DEFAULT_WATCHLIST:
        if w.symbol.lower() in low:
            return w.symbol
    for word, symbol in _ALIASES.items():
        if re.search(rf"\b{re.escape(word)}\b", low):
            return symbol
    return None


def _format_analysis(a: TickerAnalysis) -> str:
    ind, snap = a.indicators, a.snapshot
    rsi = f"{ind.rsi_14:.1f}" if ind.rsi_14 is not None else "n/a"
    trend = "n/a"
    if ind.close is not None and ind.ema_50 is not None:
        trend = "above EMA50" if ind.close > ind.ema_50 else "below EMA50"
    chg = f"{snap.change_pct:+.2f}%" if snap.change_pct is not None else "n/a"
    sigs = ", ".join(s.label for s in a.signals) or "none"
    return (
        f"[Reference data for {a.symbol} ({a.name or a.symbol}, {a.currency or '?'}), "
        f"already computed — source of truth: price {snap.price}, daily change {chg}, "
        f"RSI14 {rsi}, price {trend}, signals: {sigs}.]"
    )


def _fallback_reply(data_block: str | None) -> str:
    if data_block:
        return (
            "Live news is unavailable right now, but here is the latest computed "
            f"data: {data_block} {DISCLAIMER}"
        )
    return (
        "I couldn't identify a watchlist company or fetch data/news right now. "
        "Try naming a ticker like NVDA or KGH.WA. " + DISCLAIMER
    )


async def answer_chat(
    market: YahooMarketData, llm: GeminiClient, request: ChatRequest
) -> ChatResponse:
    last = request.messages[-1].content
    symbol = resolve_symbol(last)

    data_block: str | None = None
    used_symbol: str | None = None
    if symbol:
        try:
            data_block = _format_analysis(await analyze_symbol(market, symbol))
            used_symbol = symbol
        except MarketDataError:
            data_block = None

    contents = [
        {
            "role": "model" if m.role == ChatRole.model else "user",
            "parts": [{"text": m.content}],
        }
        for m in request.messages
    ]
    if data_block:
        contents[-1]["parts"].append({"text": data_block})

    reply, sources, ok = await llm.generate_chat_reply(contents, CHAT_SYSTEM)
    if not ok:
        return ChatResponse(reply=_fallback_reply(data_block), ticker=used_symbol, sources=[])
    return ChatResponse(reply=reply, ticker=used_symbol, sources=sources)
