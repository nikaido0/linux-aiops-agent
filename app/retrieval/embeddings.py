from typing import List
from langchain_core.embeddings import Embeddings
from openai import OpenAI
from loguru import logger
from app.config import config


class DashScopeEmbeddings(Embeddings):
    """DashScope text-embedding-v4 封装（OpenAI 兼容模式）"""

    def __init__(self):
        if not config.dashscope_api_key or config.dashscope_api_key == "your-api-key-here":
            raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

        self.client = OpenAI(
            api_key=config.dashscope_api_key,
            base_url=config.dashscope_base_url,
        )
        self.model = config.dashscope_embedding_model
        self.dimensions = 1024
        logger.info(f"DashScope Embeddings 初始化完成, model={self.model}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.model, input=texts, dimensions=self.dimensions, encoding_format="float"
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.model, input=text, dimensions=self.dimensions, encoding_format="float"
        )
        return response.data[0].embedding
