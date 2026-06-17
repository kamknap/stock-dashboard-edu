"""Default watchlist.

The watchlist is the universe of tickers the app analyses. It is configurable
and will later be stored in Firestore (phase 7); this module is the in-code
default and the single source of symbol metadata.

Symbols are **Yahoo Finance** symbols (the data source chosen in phase 2):
US tickers are plain, Warsaw GPW uses the `.WA` suffix, Korea uses `.KS`.
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
    WatchItem("MSFT", "Microsoft", "US", "USD"),
    WatchItem("NVDA", "Nvidia", "US", "USD"),
    WatchItem("AMD", "Advanced Micro Devices", "US", "USD"),
    WatchItem("GOOGL", "Alphabet", "US", "USD"),
    WatchItem("ASML", "ASML Holding", "US", "USD"),
    WatchItem("ABNB", "Airbnb", "US", "USD"),
    WatchItem("BKNG", "Booking Holdings", "US", "USD"),
    WatchItem("005930.KS", "Samsung Electronics", "KR", "KRW"),
    WatchItem("KGH.WA", "KGHM Polska Miedz", "PL", "PLN"),
)

DEFAULT_SYMBOLS: tuple[str, ...] = tuple(item.symbol for item in DEFAULT_WATCHLIST)

_BY_SYMBOL = {item.symbol: item for item in DEFAULT_WATCHLIST}


def get_watch_item(symbol: str) -> WatchItem | None:
    return _BY_SYMBOL.get(symbol)
