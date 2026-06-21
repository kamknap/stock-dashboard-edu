"""Daily report assembly.

Selects the most "notable" names of the week from the candidate pool (largest
absolute weekly move), then ties the deterministic per-ticker analysis and Top
movers to the LLM layers: the per-report narrative and the long-form Daily
Brief. Both LLM calls run concurrently. A failing ticker is skipped rather than
failing the whole report; a failing LLM call falls back deterministically.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.models.analysis import TickerAnalysis
from app.models.report import DailyReport, Session
from app.services.analysis import analyze_symbol
from app.services.llm import GeminiClient
from app.services.market_data import MarketDataError, YahooMarketData
from app.services.movers import changes_from_chart, compute_top_movers
from app.watchlist import DEFAULT_SYMBOLS


def infer_session(now: datetime) -> Session:
    """Morning before noon, afternoon otherwise (matches the 09:00/15:00 jobs)."""
    return "morning" if now.hour < 12 else "afternoon"


async def _safe_analyze(market: YahooMarketData, symbol: str) -> TickerAnalysis | None:
    try:
        return await analyze_symbol(market, symbol)
    except MarketDataError:
        return None


async def select_notable_symbols(
    market: YahooMarketData,
    *,
    count: int,
    weekly_sessions: int,
    pool: list[str] | None = None,
) -> list[str]:
    """Pick the `count` pool symbols with the largest absolute weekly move."""
    pool = list(pool) if pool else list(DEFAULT_SYMBOLS)
    charts = await market.get_charts(pool)
    scored: list[tuple[float, str]] = []
    for sym in pool:
        chart = charts.get(sym)
        if chart is None:
            continue
        _, _, weekly = changes_from_chart(chart, weekly_sessions)
        if weekly is None:
            continue
        scored.append((abs(weekly), sym))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [sym for _, sym in scored[:count]]
    return selected or pool[:count]


async def build_daily_report(
    market: YahooMarketData,
    llm: GeminiClient,
    *,
    session: Session | None = None,
    symbols: list[str] | None = None,
) -> DailyReport:
    settings = get_settings()
    now = datetime.now(ZoneInfo(settings.report_timezone))
    session = session or infer_session(now)

    if symbols:
        chosen = list(symbols)
    else:
        chosen = await select_notable_symbols(
            market,
            count=settings.watchlist_size,
            weekly_sessions=settings.movers_weekly_sessions,
        )

    analyses = await asyncio.gather(*(_safe_analyze(market, s) for s in chosen))
    tickers = [a for a in analyses if a is not None]

    movers = await compute_top_movers(market, chosen)

    # Narrative and Daily Brief are independent LLM calls -> run them together.
    (narrative, sources, llm_ok), (brief, _brief_ok) = await asyncio.gather(
        llm.generate_report_narrative(tickers, movers),
        llm.generate_daily_brief(tickers, movers, now=now),
    )

    return DailyReport(
        date=now.strftime("%Y-%m-%d"),
        session=session,
        generated_at=now,
        tickers=tickers,
        top_movers=movers,
        narrative=narrative,
        daily_brief=brief,
        sources=sources,
        llm_ok=llm_ok,
    )
