"""Daily report assembly.

Ties the deterministic layers (per-ticker analysis + Top movers) to the LLM
narrative into one DailyReport. A failing ticker is skipped rather than failing
the whole report. Persistence to Firestore is added in phase 7.
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
from app.services.movers import compute_top_movers
from app.watchlist import DEFAULT_SYMBOLS


def infer_session(now: datetime) -> Session:
    """Morning before noon, afternoon otherwise (matches the 09:00/15:00 jobs)."""
    return "morning" if now.hour < 12 else "afternoon"


async def _safe_analyze(
    market: YahooMarketData, symbol: str
) -> TickerAnalysis | None:
    try:
        return await analyze_symbol(market, symbol)
    except MarketDataError:
        return None


async def build_daily_report(
    market: YahooMarketData,
    llm: GeminiClient,
    *,
    session: Session | None = None,
    symbols: list[str] | None = None,
) -> DailyReport:
    settings = get_settings()
    symbols = list(symbols) if symbols else list(DEFAULT_SYMBOLS)
    now = datetime.now(ZoneInfo(settings.report_timezone))
    session = session or infer_session(now)

    analyses = await asyncio.gather(*(_safe_analyze(market, s) for s in symbols))
    tickers = [a for a in analyses if a is not None]

    movers = await compute_top_movers(market, symbols)
    narrative, sources, llm_ok = await llm.generate_report_narrative(tickers, movers)

    return DailyReport(
        date=now.strftime("%Y-%m-%d"),
        session=session,
        generated_at=now,
        tickers=tickers,
        top_movers=movers,
        narrative=narrative,
        sources=sources,
        llm_ok=llm_ok,
    )
