"""Shared FastAPI dependencies."""
from fastapi import Request

from app.services.market_data import YahooMarketData


def get_market(request: Request) -> YahooMarketData:
    """Return the app-wide market-data service created in the lifespan handler."""
    return request.app.state.market
