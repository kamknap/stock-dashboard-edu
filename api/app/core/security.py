"""Security dependencies."""
import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings

SCHEDULER_SECRET_HEADER = "X-Scheduler-Secret"


async def verify_scheduler_secret(
    x_scheduler_secret: str | None = Header(
        default=None, alias=SCHEDULER_SECRET_HEADER
    ),
) -> None:
    """Protect endpoints meant to be called only by the scheduler.

    The GitHub Actions cron must send the shared secret in the
    `X-Scheduler-Secret` header. Comparison is constant-time to avoid timing
    attacks. Raises 401 on a missing or mismatched secret.
    """
    expected = get_settings().run_analysis_secret
    if not x_scheduler_secret or not secrets.compare_digest(
        x_scheduler_secret, expected
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing scheduler secret.",
        )
