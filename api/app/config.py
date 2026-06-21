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
    port: int = 8080
    allowed_origins: str = "http://localhost:5173"

    # ---- Scheduler protection ----
    run_analysis_secret: str = "change-me"

    # ---- Market data (Yahoo Finance chart endpoint) ----
    cache_ttl_seconds: float = 300.0
    http_timeout_seconds: float = 15.0
    market_max_concurrency: int = 4
    market_max_retries: int = 3
    market_default_range: str = "6mo"
    market_default_interval: str = "1d"

    # ---- Top movers ----
    movers_count: int = 5
    movers_weekly_sessions: int = 5
    # How many 'notable' names to select for the report watchlist.
    watchlist_size: int = 9

    # ---- LLM (Gemini) ----
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_base: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_timeout_seconds: float = 30.0
    gemini_temperature: float = 0.4
    # Timezone for the report date and morning/afternoon session inference.
    report_timezone: str = "Europe/Warsaw"

    # ---- External market / LLM APIs ----
    finnhub_api_key: str = ""
    gemini_api_key: str = ""
    twelve_data_api_key: str = ""

    # ---- Firestore / GCP (phase 7) ----
    gcp_project_id: str = ""
    google_application_credentials: str = ""
    # Firebase Realtime Database URL (e.g. https://<proj>-default-rtdb.<region>.firebasedatabase.app).
    firebase_db_url: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse the comma-separated origins into a clean list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
