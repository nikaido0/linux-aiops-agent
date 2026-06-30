"""AIOps 诊断接口 - 流式"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.aiops_service import aiops_service
import json

router = APIRouter()


class AIOpsRequest(BaseModel):
    input: str
    session_id: str = "default"


@router.post("/api/aiops")
async def aiops(req: AIOpsRequest):
    """AIOps 流式诊断"""
    async def event_stream():
        async for event in aiops_service.execute(req.input, req.session_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
