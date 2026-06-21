"""Candidate pool for the daily report.

Instead of a fixed list, each report selects the most "notable" names of the
week from this pool (largest absolute weekly move). Symbols are Yahoo Finance
symbols: US tickers are plain, Warsaw GPW uses `.WA`, Korea uses `.KS`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WatchItem:
    symbol: str  # Yahoo Finance symbol
    name: str
    market: str  # "US" | "PL" | "KR"
    currency: str


DEFAULT_WATCHLIST: tuple[WatchItem, ...] = (
    WatchItem("AAPL", "Apple", "US", "USD"),
    WatchItem("MSFT", "Microsoft", "US", "USD"),
    WatchItem("NVDA", "Nvidia", "US", "USD"),
    WatchItem("AMD", "Advanced Micro Devices", "US", "USD"),
    WatchItem("GOOGL", "Alphabet", "US", "USD"),
    WatchItem("AMZN", "Amazon", "US", "USD"),
    WatchItem("META", "Meta Platforms", "US", "USD"),
    WatchItem("TSLA", "Tesla", "US", "USD"),
    WatchItem("AVGO", "Broadcom", "US", "USD"),
    WatchItem("NFLX", "Netflix", "US", "USD"),
    WatchItem("ADBE", "Adobe", "US", "USD"),
    WatchItem("CRM", "Salesforce", "US", "USD"),
    WatchItem("INTC", "Intel", "US", "USD"),
    WatchItem("QCOM", "Qualcomm", "US", "USD"),
    WatchItem("ORCL", "Oracle", "US", "USD"),
    WatchItem("IBM", "IBM", "US", "USD"),
    WatchItem("ABNB", "Airbnb", "US", "USD"),
    WatchItem("BKNG", "Booking Holdings", "US", "USD"),
    WatchItem("UBER", "Uber Technologies", "US", "USD"),
    WatchItem("DIS", "Walt Disney", "US", "USD"),
    WatchItem("PLTR", "Palantir", "US", "USD"),
    WatchItem("MU", "Micron Technology", "US", "USD"),
    WatchItem("COIN", "Coinbase", "US", "USD"),
    WatchItem("ASML", "ASML Holding", "US", "USD"),
    WatchItem("005930.KS", "Samsung Electronics", "KR", "KRW"),
    WatchItem("KGH.WA", "KGHM Polska Miedz", "PL", "PLN"),
)

DEFAULT_SYMBOLS: tuple[str, ...] = tuple(item.symbol for item in DEFAULT_WATCHLIST)

_BY_SYMBOL = {item.symbol: item for item in DEFAULT_WATCHLIST}


def get_watch_item(symbol: str) -> WatchItem | None:
    return _BY_SYMBOL.get(symbol)
