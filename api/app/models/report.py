"""Daily report models.

A report bundles the deterministic per-ticker analysis and Top movers with the
LLM's narrative layer. The narrative is purely descriptive (context + risks);
it never overrides the numbers and never gives buy/sell advice.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.analysis import TickerAnalysis
from app.models.movers import TopMovers
from app.models.schemas import DISCLAIMER, Source

Session = Literal["morning", "afternoon"]


class LLMNarrative(BaseModel):
    """Validated JSON returned by Gemini (the narrative layer only)."""

    market_summary: str
    # Map of ticker symbol -> short context note.
    ticker_notes: dict[str, str] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)


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
