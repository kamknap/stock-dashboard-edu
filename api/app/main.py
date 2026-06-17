"""FastAPI application entry point.

Educational stock-market analysis backend. Not a trading bot and not investment
advice. Read-only / analytical only.
"""
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_analysis,
    routes_chat,
    routes_health,
    routes_market,
    routes_reports,
)
from app.config import get_settings
from app.models.schemas import DISCLAIMER
from app.services.cache import TTLCache
from app.services.llm import GeminiClient
from app.services.market_data import YahooMarketData
from app.services.store import create_report_store

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Own one shared httpx client + cache + services for the app's life."""
    client = httpx.AsyncClient()
    cache = TTLCache(settings.cache_ttl_seconds)
    app.state.http_client = client
    app.state.cache = cache
    app.state.market = YahooMarketData(client, cache, settings=settings)
    app.state.llm = GeminiClient(client, settings=settings)
    app.state.store = create_report_store(settings)
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(
    title="Stock Dashboard API",
    version="0.4.0",
    description=(
        "Educational stock-market analysis backend. Not a trading bot and not "
        "investment advice."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_analysis.router)
app.include_router(routes_chat.router)
app.include_router(routes_market.router)
app.include_router(routes_reports.router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "service": "stock-dashboard-api",
        "version": app.version,
        "docs": "/docs",
        "disclaimer": DISCLAIMER,
    }
