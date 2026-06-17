"""Report read endpoints (public, for the frontend)."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_store
from app.models.report import DailyReport, Session
from app.services.store import ReportStore

router = APIRouter(tags=["reports"])


@router.get("/reports/latest", response_model=DailyReport)
async def latest_report(store: ReportStore = Depends(get_store)) -> DailyReport:
    report = await store.latest()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No reports yet.")
    return report


@router.get("/reports/{date}/{session}", response_model=DailyReport)
async def report_by_date(
    date: str, session: Session, store: ReportStore = Depends(get_store)
) -> DailyReport:
    report = await store.get(date, session)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report
