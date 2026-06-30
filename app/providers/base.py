from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings


class BaseProvider(ABC):
    """模型提供商抽象基类"""

    @abstractmethod
    def create_llm(self, **kwargs) -> BaseChatModel:
        """创建语言模型实例"""
        ...

    @abstractmethod
    def create_embeddings(self, **kwargs) -> Embeddings:
        """创建嵌入模型实例"""
        ...
