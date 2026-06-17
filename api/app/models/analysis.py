"""Analysis models: indicators, signals, and the per-ticker analysis bundle.

These are the deterministic outputs computed in Python. The LLM (phases 5-6)
consumes them as already-decided facts; it never recomputes or overrides them.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.market import Snapshot
from app.models.schemas import DISCLAIMER


class Indicators(BaseModel):
    """Latest values of the technical indicators."""

    as_of: datetime | None = None
    close: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None


class Signal(BaseModel):
    """An explicit rule-based observation. `direction` is a technical reading
    (up/down/neutral), NOT a buy/sell recommendation."""

    code: str
    label: str
    detail: str
    direction: Literal["up", "down", "neutral"] = "neutral"


class TickerAnalysis(BaseModel):
    symbol: str
    name: str | None = None
    currency: str | None = None
    snapshot: Snapshot
    indicators: Indicators
    signals: list[Signal]
    disclaimer: str = DISCLAIMER
