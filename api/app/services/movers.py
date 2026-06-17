"""Top movers ranking, computed from the watchlist's cached candles.

No extra API calls: it reuses the same chart data the reports and chat use.
Daily change = last price vs the prior daily close; weekly change = last price
vs the close N trading sessions ago. Gainers/losers are partitioned by sign so
the two lists never overlap.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.models.movers import MoverItem, MoversWindow, TopMovers
from app.services.market_data import ChartData, YahooMarketData
from app.watchlist import DEFAULT_SYMBOLS, get_watch_item


def pct_change(price: float | None, prev: float | None) -> float | None:
    if price is None or not prev:
        return None
    return (float(price) / float(prev) - 1.0) * 100.0


def changes_from_chart(
    chart: ChartData, weekly_sessions: int
) -> tuple[float | None, float | None, float | None]:
    """Return (price, daily_pct, weekly_pct) for one chart."""
    closes = chart.candles.close
    if not closes:
        return None, None, None
    price = chart.market_price if chart.market_price is not None else closes[-1]
    daily_prev = closes[-2] if len(closes) >= 2 else None
    weekly_prev = closes[-(weekly_sessions + 1)] if len(closes) > weekly_sessions else None
    return price, pct_change(price, daily_prev), pct_change(price, weekly_prev)


def rank(items: list[MoverItem], count: int) -> tuple[list[MoverItem], list[MoverItem]]:
    """Partition by sign: gainers (pct > 0, desc) and losers (pct < 0, asc)."""
    gainers = sorted(
        (i for i in items if i.change_pct > 0), key=lambda x: x.change_pct, reverse=True
    )[:count]
    losers = sorted((i for i in items if i.change_pct < 0), key=lambda x: x.change_pct)[:count]
    return list(gainers), list(losers)


async def compute_top_movers(
    market: YahooMarketData,
    symbols: list[str] | None = None,
    *,
    count: int | None = None,
    weekly_sessions: int | None = None,
) -> TopMovers:
    settings = get_settings()
    symbols = list(symbols) if symbols else list(DEFAULT_SYMBOLS)
    count = count or settings.movers_count
    weekly_sessions = weekly_sessions or settings.movers_weekly_sessions

    charts = await market.get_charts(symbols)

    daily_items: list[MoverItem] = []
    weekly_items: list[MoverItem] = []
    for sym in symbols:
        chart = charts.get(sym)
        if chart is None:
            continue
        item = get_watch_item(sym)
        name = item.name if item else None
        currency = chart.candles.currency
        price, daily_pct, weekly_pct = changes_from_chart(chart, weekly_sessions)
        if daily_pct is not None:
            daily_items.append(
                MoverItem(symbol=sym, name=name, currency=currency, price=price, change_pct=daily_pct)
            )
        if weekly_pct is not None:
            weekly_items.append(
                MoverItem(symbol=sym, name=name, currency=currency, price=price, change_pct=weekly_pct)
            )

    dg, dl = rank(daily_items, count)
    wg, wl = rank(weekly_items, count)
    return TopMovers(
        as_of=datetime.now(timezone.utc),
        count=count,
        daily=MoversWindow(window="daily", gainers=dg, losers=dl),
        weekly=MoversWindow(window="weekly", gainers=wg, losers=wl),
    )
