"""Top movers models.

Percentage changes are currency-agnostic ratios, so US/PL/KR tickers are
directly comparable in one ranking even though their prices are in USD/PLN/KRW.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.schemas import DISCLAIMER


class MoverItem(BaseModel):
    symbol: str
    name: str | None = None
    currency: str | None = None
    price: float | None = None
    change_pct: float


class MoversWindow(BaseModel):
    window: str  # "daily" | "weekly"
    gainers: list[MoverItem]
    losers: list[MoverItem]


class TopMovers(BaseModel):
    as_of: datetime
    count: int
    daily: MoversWindow
    weekly: MoversWindow
    disclaimer: str = DISCLAIMER
