"""Report persistence.

Reports are stored under `reports/{date}_{session}` (e.g. "2026-06-17_morning").
Uses Firebase Realtime Database (Spark plan, no billing card required) via the
firebase-admin SDK when configured; otherwise falls back to an in-memory store
so the app runs locally without credentials. firebase-admin is imported lazily,
so the dependency is only needed when RTDB is actually configured.

The admin SDK calls are blocking, so they run in a worker thread to avoid
blocking the event loop. "latest" is resolved client-side (report volume is
tiny: two per day), which avoids needing a RTDB index.
"""
from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod

from app.config import Settings, get_settings
from app.models.report import DailyReport

_ROOT = "reports"


def _doc_id(date: str, session: str) -> str:
    # RTDB keys may not contain '.', '$', '#', '[', ']', '/'. Our ids use only
    # digits, '-' and '_', so they are safe.
    return f"{date}_{session}"


class ReportStore(ABC):
    @abstractmethod
    async def save(self, report: DailyReport) -> None: ...

    @abstractmethod
    async def get(self, date: str, session: str) -> DailyReport | None: ...

    @abstractmethod
    async def latest(self) -> DailyReport | None: ...


class InMemoryReportStore(ReportStore):
    """Process-local fallback (data lost on restart). Good for local dev/tests."""

    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}

    async def save(self, report: DailyReport) -> None:
        self._docs[_doc_id(report.date, report.session)] = report.model_dump(mode="json")

    async def get(self, date: str, session: str) -> DailyReport | None:
        raw = self._docs.get(_doc_id(date, session))
        return DailyReport.model_validate(raw) if raw else None

    async def latest(self) -> DailyReport | None:
        if not self._docs:
            return None
        # generated_at is an ISO-8601 string -> lexicographic sort is chronological.
        raw = max(self._docs.values(), key=lambda d: d["generated_at"])
        return DailyReport.model_validate(raw)


class RealtimeDbReportStore(ReportStore):
    def __init__(self, settings: Settings) -> None:
        if settings.google_application_credentials:
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS", settings.google_application_credentials
            )
        import firebase_admin
        from firebase_admin import credentials, db

        self._db = db
        if not firebase_admin._apps:
            cred = (
                credentials.Certificate(settings.google_application_credentials)
                if settings.google_application_credentials
                else credentials.ApplicationDefault()
            )
            firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase_db_url})

    async def save(self, report: DailyReport) -> None:
        payload = report.model_dump(mode="json")
        await asyncio.to_thread(
            lambda: self._db.reference(_ROOT)
            .child(_doc_id(report.date, report.session))
            .set(payload)
        )

    async def get(self, date: str, session: str) -> DailyReport | None:
        raw = await asyncio.to_thread(
            lambda: self._db.reference(_ROOT).child(_doc_id(date, session)).get()
        )
        return DailyReport.model_validate(raw) if raw else None

    async def latest(self) -> DailyReport | None:
        data = await asyncio.to_thread(lambda: self._db.reference(_ROOT).get())
        if not data:
            return None
        raw = max(data.values(), key=lambda d: d.get("generated_at", ""))
        return DailyReport.model_validate(raw)


def create_report_store(settings: Settings | None = None) -> ReportStore:
    """RTDB when configured, else in-memory. Never raises on misconfig."""
    settings = settings or get_settings()
    if settings.firebase_db_url and settings.google_application_credentials:
        try:
            return RealtimeDbReportStore(settings)
        except Exception:  # noqa: BLE001 — fall back rather than crash on boot
            return InMemoryReportStore()
    return InMemoryReportStore()
