"""对话接口 - 流式（SSE）"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.agent_service import agent_service
import json

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"


@router.post("/api/chat_stream")
async def chat_stream(req: ChatRequest):
    """流式对话 (SSE)"""
    async def event_stream():
        async for event in agent_service.query_stream(req.question, req.session_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
