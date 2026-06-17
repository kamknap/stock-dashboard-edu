"""Pydantic request/response models shared across the API."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# Shown on every analytical surface. Keep wording consistent with the frontend.
DISCLAIMER = (
    "Educational tool, not investment advice. Indicators and commentary are "
    "for learning purposes only and must not be used to make financial decisions."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---- /health ----
class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    environment: str
    timestamp: datetime = Field(default_factory=_utcnow)


# ---- /run-analysis ----
class RunAnalysisResponse(BaseModel):
    status: Literal["ok"] = "ok"
    stub: bool = True
    detail: str = "run-analysis stub; indicator pipeline added in later phases."
    timestamp: datetime = Field(default_factory=_utcnow)


# ---- /chat ----
class ChatRole(str, Enum):
    """Gemini-style roles: the user and the model."""

    user = "user"
    model = "model"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    stub: bool = True
    disclaimer: str = DISCLAIMER
    timestamp: datetime = Field(default_factory=_utcnow)
