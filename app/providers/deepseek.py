from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from app.config import config
from .base import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek V4 Flash 提供商（OpenAI 兼容接口）"""

    def create_llm(self, **kwargs) -> ChatOpenAI:
        merged = {
            "model": config.deepseek_model,
            "api_key": config.deepseek_api_key,
            "base_url": config.deepseek_base_url,
            "temperature": kwargs.pop("temperature", 0.7),
            **kwargs,
        }
        return ChatOpenAI(**merged)

    def create_embeddings(self, **kwargs) -> Embeddings:
        # DeepSeek 不提供 embedding 服务，改用 DashScope
        raise NotImplementedError("DeepSeek does not provide embedding service")
