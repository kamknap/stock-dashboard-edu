"""Gemini narrative layer.

For the daily report the model receives the already-computed
indicators/signals/movers as the source of truth and only writes the narrative
(context + risks), grounded with Google Search. On 2.5 models, forced JSON and
grounding cannot be combined, so we ask for JSON in the prompt and parse it
defensively, with a deterministic fallback so the report is never empty.

The same client also powers the chat agent (free-form grounded text) and the
long-form Daily Brief (structured, sectioned world-news context).
"""
from __future__ import annotations

import json
from datetime import datetime

import httpx
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.models.analysis import TickerAnalysis
from app.models.movers import MoversWindow, TopMovers
from app.models.report import BriefSection, DailyBrief, LLMNarrative
from app.models.schemas import Source

_REPORT_INSTRUCTION = (
    "You are a financial-market analyst writing an EDUCATIONAL market-context "
    "report. The indicators and signals below were computed deterministically "
    "and are the source of truth: do not recompute, contradict, or invent "
    "numbers. Use Google Search to add fresh, relevant news context and risks "
    "for these companies as of today. Do NOT give buy/sell/hold advice and do "
    "NOT predict future prices. Return ONLY a single JSON object, with no "
    "markdown and no code fences, with exactly these keys: "
    '"headline" (string, ONE short editorial takeaway of 6 to 10 words, like a '
    "newspaper headline, no ticker symbols required, no buy/sell), "
    '"lede" (string, exactly 2 sentences that set the scene, distinct from the '
    "headline and not a verbatim copy of market_summary), "
    '"market_summary" (string, 3-6 sentences on the overall context), '
    '"highlights" (array of exactly 3 short plain sentences answering "what '
    'matters today", each referencing a concrete figure from the data), '
    '"ticker_notes" (object mapping each ticker SYMBOL to ONE concise sentence '
    "of context/news), "
    '"opportunities" (array of 3-6 short positive-outlook strings), '
    '"risks" (array of 3-6 short risk strings). '
    "Use plain punctuation and do not use em dashes; prefer commas or periods."
)

_BRIEF_INSTRUCTION = (
    "You are writing an EDUCATIONAL 'Daily Brief': long-form context on world "
    "events that could move markets, for a reader catching up over coffee. Use "
    "Google Search for fresh, current context. Do NOT give buy/sell/hold advice "
    "and do NOT predict prices; explain what the news is, not what to do. "
    "Return ONLY a single JSON object, no markdown and no code fences, with "
    "exactly these keys: "
    '"title" (string, a short editorial title of 4 to 8 words), '
    '"lede" (string, exactly 2 sentences framing the day), '
    '"sections" (array of 3 to 4 objects, each {"heading": string, "body": '
    "string of 1-2 short paragraphs}; prefer the headings 'Macro & rates', "
    "'Tech & semiconductors', 'Geopolitics & trade', 'Europe & Warsaw' where "
    "relevant), "
    '"pull_quote" (string, ONE short standalone sentence worth highlighting), '
    '"watch" (array of exactly 3 short strings: what to watch this week). '
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

    # ---- daily brief (structured, sectioned) ----
    async def generate_daily_brief(
        self, tickers: list[TickerAnalysis], movers: TopMovers, *, now: datetime
    ) -> tuple[DailyBrief, bool]:
        """Return (brief, ok). Falls back to a deterministic brief on failure."""
        body = self._body(self._build_brief_prompt(tickers, movers))
        try:
            payload = await self._post(body)
        except (GeminiError, httpx.HTTPError):
            return self._brief_fallback(tickers, movers, now=now), False

        sources = self._extract_sources(payload)
        data = self._parse_json(self._text_from(payload))
        if data is None:
            return self._brief_fallback(tickers, movers, now=now), False
        try:
            brief = DailyBrief(
                title=str(data.get("title") or "What's moving markets today"),
                lede=str(data.get("lede") or ""),
                updated_at=now,
                sections=data.get("sections") or [],
                pull_quote=(str(data["pull_quote"]) if data.get("pull_quote") else None),
                watch=[str(w) for w in (data.get("watch") or [])][:3],
                sources=sources,
                ai_generated=True,
            )
        except ValidationError:
            return self._brief_fallback(tickers, movers, now=now), False
        if not brief.sections:
            return self._brief_fallback(tickers, movers, now=now), False
        return brief, True

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

    # ---- prompts ----
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

    def _build_brief_prompt(
        self, tickers: list[TickerAnalysis], movers: TopMovers
    ) -> str:
        symbols = ", ".join(t.symbol for t in tickers) or "major US and EU names"
        lines = [
            _BRIEF_INSTRUCTION,
            "",
            f"The reader follows these names: {symbols}.",
            "Frame the world-news context around what could matter for them.",
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

    # ---- fallbacks ----
    @staticmethod
    def _breadth(tickers: list[TickerAnalysis]) -> tuple[int, int]:
        n = len(tickers)
        above = sum(
            1
            for t in tickers
            if t.indicators.close is not None
            and t.indicators.ema_50 is not None
            and t.indicators.close > t.indicators.ema_50
        )
        return above, n

    @classmethod
    def _fallback(
        cls, tickers: list[TickerAnalysis], movers: TopMovers
    ) -> LLMNarrative:
        above, n = cls._breadth(tickers)
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

        headline = (
            "Most names hold above their trend"
            if n and above > n / 2
            else "Watchlist leans below its trend"
        )

        highlights = [parts[0]]
        if movers.daily.gainers:
            g = movers.daily.gainers[0]
            highlights.append(f"{g.symbol} led the tape at {g.change_pct:+.2f}%.")
        if movers.daily.losers:
            d = movers.daily.losers[0]
            highlights.append(f"{d.symbol} lagged at {d.change_pct:+.2f}%.")

        return LLMNarrative(
            headline=headline,
            market_summary=" ".join(parts),
            lede=" ".join(parts[:2]),
            highlights=highlights[:3],
            ticker_notes=notes,
            opportunities=opportunities,
            risks=[
                "Generated without live news grounding — verify against current "
                "sources before relying on this context."
            ],
        )

    @classmethod
    def _brief_fallback(
        cls, tickers: list[TickerAnalysis], movers: TopMovers, *, now: datetime
    ) -> DailyBrief:
        above, n = cls._breadth(tickers)
        lede = (
            "Live world-news context is unavailable, so this is an automated "
            f"summary of the watchlist. {above} of {n} names closed above their "
            "EMA50."
        )
        body_lines = []
        if movers.daily.gainers:
            g = movers.daily.gainers[0]
            body_lines.append(f"Top daily gainer: {g.symbol} at {g.change_pct:+.2f}%.")
        if movers.daily.losers:
            d = movers.daily.losers[0]
            body_lines.append(f"Top daily loser: {d.symbol} at {d.change_pct:+.2f}%.")
        sections = [
            BriefSection(
                heading="Market context",
                body=" ".join(body_lines) or "No standout moves on the watchlist today.",
            )
        ]
        watch = [f"{m.symbol} weekly move {m.change_pct:+.2f}%" for m in movers.weekly.gainers[:3]]
        return DailyBrief(
            title="What's moving markets today",
            lede=lede,
            updated_at=now,
            sections=sections,
            pull_quote=None,
            watch=watch,
            sources=[],
            ai_generated=False,
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
