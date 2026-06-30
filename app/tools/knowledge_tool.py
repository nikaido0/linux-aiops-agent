"""知识检索工具 - Agent 通过此工具查询知识库"""

from langchain_core.tools import tool
from loguru import logger
from app.services.knowledge_service import knowledge_service


@tool(response_format="content_and_artifact")
def retrieve_knowledge(query: str) -> tuple:
    """从 Linux 运维知识库中检索相关信息

    当用户的问题涉及 Linux 运维、故障排查、告警处理等专业知识时，
    使用此工具从知识库中获取相关的排查方案和最佳实践。

    Args:
        query: 用户的问题或查询关键词
    """
    try:
        logger.info(f"知识检索: query='{query}'")
        context = knowledge_service.search(query)
        return context or "没有找到相关信息。", []
    except Exception as e:
        logger.error(f"知识检索失败: {e}")
        return f"检索时发生错误: {e}", []
