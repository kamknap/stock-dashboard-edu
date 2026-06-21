"""Daily report models.

A report bundles the deterministic per-ticker analysis and Top movers with the
LLM's narrative layer. The narrative is purely descriptive (context + risks);
it never overrides the numbers and never gives buy/sell advice.

ticker_notes is a LIST of {symbol, note} rather than a symbol-keyed dict because
Realtime Database keys may not contain '.', and tickers like KGH.WA / 005930.KS
do. A validator accepts the model's dict output and normalises it to the list.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.analysis import TickerAnalysis
from app.models.movers import TopMovers
from app.models.schemas import DISCLAIMER, Source

Session = Literal["morning", "afternoon"]


class TickerNote(BaseModel):
    symbol: str
    note: str


class LLMNarrative(BaseModel):
    """Validated JSON returned by Gemini (the narrative layer only)."""

    # One-line editorial takeaway used as the brief headline. Optional so older
    # stored reports (and partial model output) still validate; the client
    # derives a fallback from market_summary when this is empty.
    headline: str = ""
    market_summary: str
    # 2-3 plain sentences answering "what matters today". Optional for the same
    # backward-compat reason; the client derives a fallback from the movers.
    highlights: list[str] = Field(default_factory=list)
    ticker_notes: list[TickerNote] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    @field_validator("ticker_notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value):
        """Accept either {symbol: note} (what the model returns) or a list."""
        if value is None:
            return []
        if isinstance(value, dict):
            return [{"symbol": str(k), "note": str(v)} for k, v in value.items()]
        if isinstance(value, list):
            out = []
            for item in value:
                if isinstance(item, dict) and item.get("symbol"):
                    out.append(
                        {"symbol": str(item["symbol"]), "note": str(item.get("note", ""))}
                    )
            return out
        return []


class DailyReport(BaseModel):
    date: str  # YYYY-MM-DD in the report timezone
    session: Session
    generated_at: datetime
    tickers: list[TickerAnalysis]
    top_movers: TopMovers
    narrative: LLMNarrative
    sources: list[Source] = Field(default_factory=list)
    # False when the LLM/grounding failed and a deterministic fallback was used.
    llm_ok: bool = True
    disclaimer: str = DISCLAIMER
