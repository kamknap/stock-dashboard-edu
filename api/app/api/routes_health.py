"""Health-check endpoint."""
from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness/readiness probe used by Render's health check and the scheduler."""
    return HealthResponse(environment=get_settings().environment)
