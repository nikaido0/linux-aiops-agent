"""PromptBuilder - 动态构建 SystemMessage

每次请求前从固定模板 + 本轮动态上下文构建新的 SystemMessage。
模板（prompts/system_prompt.md）本身永远不被修改。
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from langchain_core.messages import SystemMessage
from loguru import logger


class PromptBuilder:
    """系统提示构建器

    用法:
        builder = PromptBuilder()
        sys_msg = builder.build(
            question="CPU 使用率高怎么办",
            knowledge_context="【参考资料 1】...",
            tools=[tool1, tool2],
        )
    """

    def __init__(self, template_path: Optional[str] = None):
        if template_path is None:
            template_path = str(Path(__file__).resolve().parent.parent.parent / "prompts" / "system_prompt.md")
        self._template = self._load_template(template_path)
        logger.info(f"PromptBuilder 加载模板: {template_path}")

    @staticmethod
    def _load_template(path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(f"模板文件不存在: {path}，使用默认模板")
            return "你是一个专业的 Linux 运维助手。\n\n## 工具\n{tools}\n\n## 知识库\n{knowledge_context}"

    def build(
        self,
        *,
        knowledge_context: str = "",
        tools: Optional[List] = None,
        current_time: Optional[str] = None,
    ) -> SystemMessage:
        """构建当前轮次的 SystemMessage

        Args:
            knowledge_context: 本轮 RAG 检索结果（空字符串表示无检索结果）
            tools: Agent 可用工具列表
            current_time: 当前时间（可选，自动获取）

        Returns:
            SystemMessage: 包含完整上下文的系统消息
        """
        # 格式化工具列表
        tool_text = ""
        if tools:
            lines = []
            for t in tools:
                name = getattr(t, "name", str(t))
                desc = getattr(t, "description", "")
                lines.append(f"- {name}: {desc[:100]}")
            tool_text = "\n".join(lines) if lines else "暂无专用工具"

        # 当前时间
        time_str = current_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 填入模板
        content = self._template.replace("{tools}", tool_text)
        content = content.replace("{current_time}", time_str)
        content = content.replace("{knowledge_context}", knowledge_context or "本次未检索知识库")

        return SystemMessage(content=content)


prompt_builder = PromptBuilder()
