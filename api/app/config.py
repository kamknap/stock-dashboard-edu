"""Application configuration loaded from environment variables.

Values are read from the process environment and, in local development, from a
`.env` file. Secrets must never be hard-coded; see `.env.example`.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Server ----
    environment: str = "development"
    # Local default; on Render/Cloud Run the platform injects PORT.
    port: int = 8080
    # Comma-separated list of CORS origins (frontend URLs).
    allowed_origins: str = "http://localhost:5173"

    # ---- Scheduler protection ----
    run_analysis_secret: str = "change-me"

    # ---- Market data (Yahoo Finance chart endpoint) ----
    # Cache TTL for fetched chart data (seconds). Daily candles barely change
    # intraday; this mainly protects the chat path and avoids re-fetching within
    # a single analysis run.
    cache_ttl_seconds: float = 300.0
    http_timeout_seconds: float = 15.0
    # Max concurrent upstream requests when fetching the whole watchlist.
    market_max_concurrency: int = 4
    # Retries per request on 429/5xx before failing over to the next host.
    market_max_retries: int = 3
    # Default candle window used for indicators / movers.
    market_default_range: str = "6mo"
    market_default_interval: str = "1d"

    # ---- Top movers ----
    # How many gainers and losers to show per window.
    movers_count: int = 5
    # Trading sessions that define the "weekly" window.
    movers_weekly_sessions: int = 5

    # ---- External market / LLM APIs (used from phase 2 onward) ----
    finnhub_api_key: str = ""
    gemini_api_key: str = ""
    twelve_data_api_key: str = ""

    # ---- Firestore / GCP (phase 7) ----
    gcp_project_id: str = ""
    google_application_credentials: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse the comma-separated origins into a clean list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
