"""Gemini narrative layer for the daily report.

The model receives the already-computed indicators/signals/movers as the source
of truth and only writes the narrative (market context + risks), grounded with
Google Search for fresh news. On 2.5 models, forced JSON (responseSchema) and
grounding cannot be combined, so we ask for JSON in the prompt and parse it
defensively. Any failure (no key, HTTP error, unparseable JSON) falls back to a
deterministic narrative built from the numbers, so the report is never empty.
"""
from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.models.analysis import TickerAnalysis
from app.models.movers import MoversWindow, TopMovers
from app.models.report import LLMNarrative, Source

_SYSTEM_INSTRUCTION = (
    "You are a financial-market analyst writing an EDUCATIONAL market-context "
    "report. The indicators and signals below were computed deterministically "
    "and are the source of truth: do not recompute, contradict, or invent "
    "numbers. Use Google Search to add fresh, relevant news context and risks "
    "for these companies as of today. Do NOT give buy/sell/hold advice and do "
    "NOT predict future prices. Return ONLY a single JSON object, with no "
    "markdown and no code fences, with exactly these keys: "
    '"market_summary" (string, 3-6 sentences on the overall context), '
    '"ticker_notes" (object mapping each ticker SYMBOL to a 1-2 sentence '
    'context/news note), "risks" (array of 3-6 short risk strings).'
)


class GeminiError(Exception):
    pass


class GeminiClient:
    def __init__(
        self, client: httpx.AsyncClient, settings: Settings | None = None
    ) -> None:
        self._client = client
        self._settings = settings or get_settings()

    async def generate_report_narrative(
        self, tickers: list[TickerAnalysis], movers: TopMovers
    ) -> tuple[LLMNarrative, list[Source], bool]:
        """Return (narrative, sources, llm_ok). Falls back deterministically."""
        prompt = self._build_prompt(tickers, movers)
        try:
            payload = await self._call(prompt)
        except (GeminiError, httpx.HTTPError):
            return self._fallback(tickers, movers), [], False

        sources = self._extract_sources(payload)
        data = self._parse_json(self._text_from(payload))
        if data is None:
            return self._fallback(tickers, movers), sources, False
        try:
            narrative = LLMNarrative.model_validate(data)
        except ValidationError:
            return self._fallback(tickers, movers), sources, False
        return narrative, sources, True

    # ---- HTTP ----
    async def _call(self, prompt: str) -> dict:
        key = self._settings.gemini_api_key
        if not key:
            raise GeminiError("GEMINI_API_KEY is not set")
        url = (
            f"{self._settings.gemini_api_base}/models/"
            f"{self._settings.gemini_model}:generateContent"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": self._settings.gemini_temperature},
        }
        resp = await self._client.post(
            url,
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body,
            timeout=self._settings.gemini_timeout_seconds,
        )
        if resp.status_code != 200:
            raise GeminiError(f"HTTP {resp.status_code}")
        return resp.json()

    # ---- prompt ----
    def _build_prompt(self, tickers: list[TickerAnalysis], movers: TopMovers) -> str:
        lines = [_SYSTEM_INSTRUCTION, "", "Watchlist (deterministic, source of truth):"]
        lines.extend(_ticker_line(t) for t in tickers)
        lines += [
            "",
            "Top movers (daily): " + _movers_line(movers.daily),
            "Top movers (weekly): " + _movers_line(movers.weekly),
        ]
        return "\n".join(lines)

    # ---- response parsing ----
    @staticmethod
    def _text_from(payload: dict) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            return ""
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))

    @staticmethod
    def _extract_sources(payload: dict) -> list[Source]:
        candidates = payload.get("candidates") or []
        if not candidates:
            return []
        meta = candidates[0].get("groundingMetadata") or {}
        out: list[Source] = []
        seen: set[str] = set()
        for chunk in meta.get("groundingChunks") or []:
            web = chunk.get("web") or {}
            uri = web.get("uri")
            if uri and uri not in seen:
                seen.add(uri)
                out.append(Source(title=web.get("title"), url=uri))
        return out

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """Extract the first JSON object from free-form text (tolerates fences)."""
        if not text:
            return None
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    # ---- fallback ----
    @staticmethod
    def _fallback(tickers: list[TickerAnalysis], movers: TopMovers) -> LLMNarrative:
        n = len(tickers)
        above = sum(
            1
            for t in tickers
            if t.indicators.close is not None
            and t.indicators.ema_50 is not None
            and t.indicators.close > t.indicators.ema_50
        )
        parts = [
            f"Automated summary (live news unavailable). {above} of {n} watchlist "
            "names closed above their EMA50."
        ]
        if movers.daily.gainers:
            g = movers.daily.gainers[0]
            parts.append(f"Top daily gainer: {g.symbol} {g.change_pct:+.2f}%.")
        if movers.daily.losers:
            d = movers.daily.losers[0]
            parts.append(f"Top daily loser: {d.symbol} {d.change_pct:+.2f}%.")

        notes: dict[str, str] = {}
        for t in tickers:
            ind = t.indicators
            trend = (
                "above EMA50"
                if ind.close is not None
                and ind.ema_50 is not None
                and ind.close > ind.ema_50
                else "below EMA50"
            )
            rsi = f"RSI {ind.rsi_14:.0f}" if ind.rsi_14 is not None else "RSI n/a"
            codes = ", ".join(s.code for s in t.signals) or "no signals"
            notes[t.symbol] = f"{rsi}, {trend}; {codes}."

        return LLMNarrative(
            market_summary=" ".join(parts),
            ticker_notes=notes,
            risks=[
                "Generated without live news grounding — verify against current "
                "sources before relying on this context."
            ],
        )


def _ticker_line(t: TickerAnalysis) -> str:
    ind, snap = t.indicators, t.snapshot
    rsi = f"{ind.rsi_14:.1f}" if ind.rsi_14 is not None else "n/a"
    trend = "n/a"
    if ind.close is not None and ind.ema_50 is not None:
        trend = "above EMA50" if ind.close > ind.ema_50 else "below EMA50"
    macd = "n/a"
    if ind.macd is not None and ind.macd_signal is not None:
        macd = "above signal" if ind.macd > ind.macd_signal else "below signal"
    chg = f"{snap.change_pct:+.2f}%" if snap.change_pct is not None else "n/a"
    sigs = ", ".join(s.label for s in t.signals) or "none"
    return (
        f"- {t.symbol} ({t.name or t.symbol}, {t.currency or '?'}): "
        f"price {snap.price}, daily {chg}, RSI14 {rsi}, {trend}, MACD {macd}; "
        f"signals: {sigs}"
    )


def _movers_line(window: MoversWindow) -> str:
    gainers = ", ".join(f"{m.symbol} {m.change_pct:+.2f}%" for m in window.gainers) or "none"
    losers = ", ".join(f"{m.symbol} {m.change_pct:+.2f}%" for m in window.losers) or "none"
    return f"gainers: {gainers}; losers: {losers}"
