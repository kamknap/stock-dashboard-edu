"""Daily report models.

A report bundles the deterministic per-ticker analysis and Top movers with the
LLM's narrative layer. The narrative is purely descriptive (context + risks);
it never overrides the numbers and never gives buy/sell advice.

ticker_notes is a LIST of {symbol, note} rather than a symbol-keyed dict because
Realtime Database keys may not contain '.', and tickers like KGH.WA / 005930.KS
do. A validator accepts the model's dict output and normalises it to the list.

daily_brief is an optional long-form, sectioned market overview (the "Daily
Brief" modal). It is generated and cached once per report run, so the modal
just reads it off the report rather than calling the model on every open.
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

    # Short editorial takeaway (6-10 words) used as the brief headline. Distinct
    # from the lede. Optional so older stored reports / partial model output
    # still validate; the client derives a fallback when this is empty.
    headline: str = ""
    market_summary: str
    # Two-sentence lede shown under the headline (distinct from the headline and
    # from the full market_summary). Optional for the same backward-compat reason.
    lede: str = ""
    # 2-3 plain sentences answering "what matters today".
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
                if isinstance(item, TickerNote):
                    out.append(item)
                elif isinstance(item, dict) and item.get("symbol"):
                    out.append(
                        {"symbol": str(item["symbol"]), "note": str(item.get("note", ""))}
                    )
            return out
        return []


class BriefSection(BaseModel):
    heading: str
    body: str


class DailyBrief(BaseModel):
    """Long-form, sectioned market overview for the Daily Brief modal."""

    title: str
    lede: str
    updated_at: datetime
    sections: list[BriefSection] = Field(default_factory=list)
    pull_quote: str | None = None
    watch: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    # False when the model/grounding failed and a deterministic fallback was used.
    ai_generated: bool = True

    @field_validator("sections", mode="before")
    @classmethod
    def _normalize_sections(cls, value):
        """Drop malformed entries from raw model output; pass through real ones."""
        if not isinstance(value, list):
            return []
        out = []
        for item in value:
            if isinstance(item, BriefSection):
                out.append(item)
            elif isinstance(item, dict) and item.get("heading") and item.get("body"):
                out.append({"heading": str(item["heading"]), "body": str(item["body"])})
        return out


class DailyReport(BaseModel):
    date: str  # YYYY-MM-DD in the report timezone
    session: Session
    generated_at: datetime
    tickers: list[TickerAnalysis]
    top_movers: TopMovers
    narrative: LLMNarrative
    daily_brief: DailyBrief | None = None
    sources: list[Source] = Field(default_factory=list)
    # False when the LLM/grounding failed and a deterministic fallback was used.
    llm_ok: bool = True
    disclaimer: str = DISCLAIMER
