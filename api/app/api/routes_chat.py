"""Analytical chat endpoint (stub).

Accepts the conversation history. The real implementation (phase 6) wires
Gemini Flash function calling (the `get_stock_data` tool) plus Google Search
grounding. The agent's answer is always framed as context and risks — current
trend, key indicators, fresh news, risks — never a buy/sell verdict, and always
carries the educational disclaimer.
"""
from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    last = request.messages[-1].content
    reply = (
        "Chat stub. The analytical agent (Gemini function calling + grounding) "
        "is added in phase 6. It will return market context and risks, never a "
        f"buy/sell verdict. Received message: {last[:200]}"
    )
    return ChatResponse(reply=reply)
