"""Scheduled analysis endpoint (stub).

Called twice a day by the GitHub Actions scheduler (09:00 / 15:00
Europe/Warsaw). Protected by a shared secret passed in the X-Scheduler-Secret
header. The real implementation — fetch watchlist data, compute indicators and
signals, rank top movers, generate the LLM report, persist to Firestore — is
added in later phases.
"""
from fastapi import APIRouter, Depends

from app.core.security import verify_scheduler_secret
from app.models.schemas import RunAnalysisResponse

router = APIRouter(tags=["analysis"])


@router.post(
    "/run-analysis",
    response_model=RunAnalysisResponse,
    dependencies=[Depends(verify_scheduler_secret)],
)
async def run_analysis() -> RunAnalysisResponse:
    return RunAnalysisResponse()
