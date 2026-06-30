"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import config
from app.api import chat, health, aiops
from app.mcp.manager import MCPManager
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{config.app_name} v{config.app_version} 启动中...")
    yield
    await MCPManager.close()
    logger.info(f"{config.app_name} 已关闭")


app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="Linux 服务器智能运维 Agent 系统",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(aiops.router)


@app.get("/")
async def root():
    return {"message": f"Welcome to {config.app_name} API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.host, port=config.port, reload=config.debug)
