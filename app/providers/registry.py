from typing import Any
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from loguru import logger
from .base import BaseProvider
from .deepseek import DeepSeekProvider


class ProviderRegistry:
    """模型提供商注册中心

    职责:
    - 管理多个模型提供商（DeepSeek, OpenAI, Claude 等）
    - 通过名称获取对应的 LLM 或 Embeddings 实例
    - 支持切换默认提供商

    用法:
        llm = ProviderRegistry.get_llm(temperature=0)
        llm = ProviderRegistry.get_llm("openai", temperature=0.3)
    """

    _providers: dict[str, BaseProvider] = {}
    _default: str = ""

    @classmethod
    def register(cls, name: str, provider: BaseProvider, default: bool = False):
        """注册提供商"""
        cls._providers[name] = provider
        if default or not cls._default:
            cls._default = name
        logger.info(f"Provider [{name}] registered, default={default}")

    @classmethod
    def get_llm(cls, name: str | None = None, **kwargs) -> BaseChatModel:
        """获取 LLM 实例"""
        provider_name = name or cls._default
        provider = cls._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider [{provider_name}] not registered")
        return provider.create_llm(**kwargs)

    @classmethod
    def get_embeddings(cls, name: str | None = None, **kwargs) -> Embeddings:
        """获取 Embeddings 实例"""
        provider_name = name or cls._default
        provider = cls._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider [{provider_name}] not registered")
        return provider.create_embeddings(**kwargs)


# 注册默认 Provider
ProviderRegistry.register("deepseek", DeepSeekProvider(), default=True)
