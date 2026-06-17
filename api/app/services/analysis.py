"""Per-ticker analysis orchestrator.

Ties the shared market-data layer to the deterministic indicator + signal
layers. Reused by the scheduled report, the chat tool, and Top movers so the
numbers are identical everywhere.
"""
from __future__ import annotations

from app.models.analysis import TickerAnalysis
from app.services import indicators, signals
from app.services.market_data import YahooMarketData
from app.watchlist import get_watch_item


async def analyze_symbol(
    market: YahooMarketData,
    symbol: str,
    *,
    range: str | None = None,
    interval: str | None = None,
) -> TickerAnalysis:
    # Both calls hit the same cached chart payload -> one upstream request.
    candles = await market.get_candles(symbol, range=range, interval=interval)
    snapshot = await market.get_snapshot(symbol, range=range, interval=interval)

    result = indicators.compute(candles)
    ctx = indicators.build_context(result.frame)
    sigs = signals.evaluate(ctx) if ctx is not None else []

    item = get_watch_item(symbol)
    return TickerAnalysis(
        symbol=symbol,
        name=item.name if item else None,
        currency=candles.currency,
        snapshot=snapshot,
        indicators=result.latest,
        signals=sigs,
    )
