"""Watchlist and market-data routes.

`/watchlist` and `/top-movers` expose watchlist-derived data. The `/market/*`
routes accept any well-formed ticker (validated by pattern) so the UI can look
up symbols beyond the watchlist; responses are cached to limit upstream load.
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_market
from app.models.analysis import TickerAnalysis
from app.models.market import Candles, Snapshot
from app.models.movers import TopMovers
from app.services.analysis import analyze_symbol
from app.services.market_data import MarketDataError, YahooMarketData
from app.services.movers import compute_top_movers
from app.watchlist import DEFAULT_WATCHLIST

router = APIRouter(tags=["market"])

# Letters, digits, dot and dash (e.g. MSFT, KGH.WA, 005930.KS, BRK-B).
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.\-]{1,15}$")


def _validate_symbol(symbol: str) -> str:
    """Reject malformed input so the endpoint can't be abused with arbitrary
    path content; any well-formed ticker is allowed (cache limits upstream load)."""
    if not _SYMBOL_RE.match(symbol):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Invalid symbol '{symbol}'."
        )
    return symbol


@router.get("/watchlist")
async def watchlist() -> list[dict]:
    return [
        {"symbol": w.symbol, "name": w.name, "market": w.market, "currency": w.currency}
        for w in DEFAULT_WATCHLIST
    ]


@router.get("/top-movers", response_model=TopMovers)
async def top_movers(market: YahooMarketData = Depends(get_market)) -> TopMovers:
    try:
        return await compute_top_movers(market)
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get("/market/{symbol}", response_model=Snapshot)
async def market_snapshot(
    symbol: str, market: YahooMarketData = Depends(get_market)
) -> Snapshot:
    _validate_symbol(symbol)
    try:
        return await market.get_snapshot(symbol)
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get("/market/{symbol}/candles", response_model=Candles)
async def market_candles(
    symbol: str,
    range: str = Query(default="6mo"),
    interval: str = Query(default="1d"),
    market: YahooMarketData = Depends(get_market),
) -> Candles:
    _validate_symbol(symbol)
    try:
        return await market.get_candles(symbol, range=range, interval=interval)
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get("/market/{symbol}/analysis", response_model=TickerAnalysis)
async def market_analysis(
    symbol: str, market: YahooMarketData = Depends(get_market)
) -> TickerAnalysis:
    _validate_symbol(symbol)
    try:
        return await analyze_symbol(market, symbol)
    except MarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
