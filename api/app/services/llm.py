"""Gemini narrative layer.

For the daily report the model receives the already-computed
indicators/signals/movers as the source of truth and only writes the narrative
(context + risks), grounded with Google Search. On 2.5 models, forced JSON and
grounding cannot be combined, so we ask for JSON in the prompt and parse it
defensively, with a deterministic fallback so the report is never empty.

The same client also powers the chat agent (free-form grounded text).
"""
from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.models.analysis import TickerAnalysis
from app.models.movers import MoversWindow, TopMovers
from app.models.report import LLMNarrative
from app.models.schemas import Source

_REPORT_INSTRUCTION = (
    "You are a financial-market analyst writing an EDUCATIONAL market-context "
    "report. The indicators and signals below were computed deterministically "
    "and are the source of truth: do not recompute, contradict, or invent "
    "numbers. Use Google Search to add fresh, relevant news context and risks "
    "for these companies as of today. Do NOT give buy/sell/hold advice and do "
    "NOT predict future prices. Return ONLY a single JSON object, with no "
    "markdown and no code fences, with exactly these keys: "
    '"market_summary" (string, 3-6 sentences on the overall context), '
    '"ticker_notes" (object mapping each ticker SYMBOL to ONE concise sentence '
    "of context/news), "
    '"opportunities" (array of 3-6 short positive-outlook strings), '
    '"risks" (array of 3-6 short risk strings). '
    "Use plain punctuation and do not use em dashes; prefer commas or periods."
)


class GeminiError(Exception):
    pass


class GeminiClient:
    def __init__(
        self, client: httpx.AsyncClient, settings: Settings | None = None
    ) -> None:
        self._client = client
        self._settings = settings or get_settings()

    # ---- report narrative (validated JSON) ----
    async def generate_report_narrative(
        self, tickers: list[TickerAnalysis], movers: TopMovers
    ) -> tuple[LLMNarrative, list[Source], bool]:
        """Return (narrative, sources, llm_ok). Falls back deterministically."""
        body = self._body(self._build_report_prompt(tickers, movers))
        try:
            payload = await self._post(body)
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

    # ---- chat (free-form grounded text) ----
    async def generate_chat_reply(
        self, contents: list[dict], system_instruction: str
    ) -> tuple[str, list[Source], bool]:
        """Return (reply_text, sources, ok). Empty text/ok=False on any failure."""
        body = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": self._settings.gemini_temperature},
        }
        try:
            payload = await self._post(body)
        except (GeminiError, httpx.HTTPError):
            return "", [], False
        text = self._text_from(payload)
        return text, self._extract_sources(payload), bool(text.strip())

    # ---- HTTP ----
    def _body(self, prompt: str) -> dict:
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": self._settings.gemini_temperature},
        }

    async def _post(self, body: dict) -> dict:
        key = self._settings.gemini_api_key
        if not key:
            raise GeminiError("GEMINI_API_KEY is not set")
        url = (
            f"{self._settings.gemini_api_base}/models/"
            f"{self._settings.gemini_model}:generateContent"
        )
        resp = await self._client.post(
            url,
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body,
            timeout=self._settings.gemini_timeout_seconds,
        )
        if resp.status_code != 200:
            raise GeminiError(f"HTTP {resp.status_code}")
        return resp.json()

    # ---- report prompt ----
    def _build_report_prompt(
        self, tickers: list[TickerAnalysis], movers: TopMovers
    ) -> str:
        lines = [_REPORT_INSTRUCTION, "", "Watchlist (deterministic, source of truth):"]
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

        opportunities = []
        if above:
            opportunities.append(
                f"{above} of {n} watchlist names are trading above their EMA50 "
                "(longer-term uptrend)."
            )
        if movers.daily.gainers:
            g = movers.daily.gainers[0]
            opportunities.append(
                f"Positive momentum: {g.symbol} leads daily gainers at {g.change_pct:+.2f}%."
            )
        if not opportunities:
            opportunities = ["No standout positives in the deterministic signals."]

        return LLMNarrative(
            market_summary=" ".join(parts),
            ticker_notes=notes,
            opportunities=opportunities,
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
