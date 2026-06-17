"""Analytical chat endpoint.

Accepts the conversation history and returns market context + risks for the
company the user mentions (never a buy/sell verdict). See app.services.chat for
the agent flow (ticker resolution -> deterministic data -> grounded narrative).
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_llm, get_market
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat import answer_chat
from app.services.llm import GeminiClient
from app.services.market_data import YahooMarketData

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    market: YahooMarketData = Depends(get_market),
    llm: GeminiClient = Depends(get_llm),
) -> ChatResponse:
    return await answer_chat(market, llm, request)
