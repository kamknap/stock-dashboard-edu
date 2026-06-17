"""Scheduled analysis endpoint.

Called twice a day by the GitHub Actions scheduler (09:00 / 15:00
Europe/Warsaw). Protected by a shared secret in the X-Scheduler-Secret header.
Builds the full daily report, persists it, and returns it.
"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_llm, get_market, get_store
from app.core.security import verify_scheduler_secret
from app.models.report import DailyReport, Session
from app.services.llm import GeminiClient
from app.services.market_data import YahooMarketData
from app.services.report import build_daily_report
from app.services.store import ReportStore

router = APIRouter(tags=["analysis"])


@router.post(
    "/run-analysis",
    response_model=DailyReport,
    dependencies=[Depends(verify_scheduler_secret)],
)
async def run_analysis(
    session: Session | None = Query(default=None),
    market: YahooMarketData = Depends(get_market),
    llm: GeminiClient = Depends(get_llm),
    store: ReportStore = Depends(get_store),
) -> DailyReport:
    report = await build_daily_report(market, llm, session=session)
    await store.save(report)
    return report
