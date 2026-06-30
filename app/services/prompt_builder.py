"""PromptBuilder - 纯角色 SystemMessage

SystemMessage 一旦构建即完全静态，不包含任何动态内容（时间、知识库、工具列表等）。
模板（prompts/system_prompt.md）本身永远不被修改。
"""

from pathlib import Path
from typing import Optional
from langchain_core.messages import SystemMessage
from loguru import logger


class PromptBuilder:
    """系统提示构建器 — 仅构建纯角色 SystemMessage"""

    def __init__(self, template_path: Optional[str] = None):
        if template_path is None:
            template_path = str(Path(__file__).resolve().parent.parent.parent / "prompts" / "system_prompt.md")
        self._content = self._load_template(template_path)
        logger.info(f"PromptBuilder 加载模板: {template_path}")

    @staticmethod
    def _load_template(path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(f"模板文件不存在: {path}，使用默认模板")
            return "你是一个专业的 Linux 运维助手。"

    def build(self) -> SystemMessage:
        """返回纯角色 SystemMessage（完全静态）"""
        return SystemMessage(content=self._content)


prompt_builder = PromptBuilder()
