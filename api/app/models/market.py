"""Market-data models.

`Candles` holds OHLCV series as parallel arrays (JSON- and DataFrame-friendly;
phase 3 indicators build a pandas DataFrame from them). `Snapshot` is the
latest price plus the deterministic daily change computed in Python.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Candles(BaseModel):
    """Daily OHLCV series for one symbol (nulls dropped, chronological)."""

    symbol: str
    currency: str | None = None
    interval: str
    range: str
    dates: list[datetime] = Field(default_factory=list)
    open: list[float] = Field(default_factory=list)
    high: list[float] = Field(default_factory=list)
    low: list[float] = Field(default_factory=list)
    close: list[float] = Field(default_factory=list)
    volume: list[int | None] = Field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.close)


class Snapshot(BaseModel):
    """Latest price and deterministic daily change for one symbol."""

    symbol: str
    currency: str | None = None
    price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    as_of: datetime
    source: str = "yahoo"
