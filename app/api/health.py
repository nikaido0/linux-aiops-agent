"""健康检查接口"""

from fastapi import APIRouter
from app.services.knowledge_service import knowledge_service

router = APIRouter()


@router.get("/api/health")
async def health():
    return {
        "status": "ok",
        "doc_count": knowledge_service.count_documents(),
    }
