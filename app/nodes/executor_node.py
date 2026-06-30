"""Executor 节点 - 执行计划中的单个步骤

使用 LLM + ToolNode 执行当前步骤。
如果 LLM 决定调用工具，自动执行并将结果返回给 LLM 生成最终答案。
"""

from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode
from loguru import logger
from app.providers.registry import ProviderRegistry
from app.tools import DEFAULT_LOCAL_TOOLS
from app.mcp.manager import MCPManager
from .state import PlanExecuteState


async def executor_node(state: PlanExecuteState) -> Dict[str, Any]:
    """执行计划中的第一个步骤"""
    plan = state.get("plan", [])
    if not plan:
        return {}

    task = plan[0]
    logger.info(f"=== Executor: {task[:60]} ===")

    try:
        local_tools = list(DEFAULT_LOCAL_TOOLS)
        mcp_tools = await MCPManager.get_tools()
        all_tools = local_tools + mcp_tools

        llm = ProviderRegistry.get_llm(temperature=0).bind_tools(all_tools)
        tool_node = ToolNode(all_tools)

        messages = [
            SystemMessage(content="执行指定的运维任务步骤，使用工具获取实际数据，不要编造结果。"),
            HumanMessage(content=f"请执行以下任务: {task}"),
        ]

        response = await llm.ainvoke(messages)

        # 如果有工具调用，执行工具
        if hasattr(response, "tool_calls") and response.tool_calls:
            messages.append(response)
            tool_results = await tool_node.ainvoke({"messages": messages})
            messages.extend(tool_results["messages"])
            response = await llm.ainvoke(messages)

        result = response.content if hasattr(response, "content") else str(response)
        logger.info(f"步骤执行完成, 结果长度: {len(result)}")

        return {"plan": plan[1:], "past_steps": [(task, result)]}

    except Exception as e:
        logger.error(f"执行失败: {e}")
        return {"plan": plan[1:], "past_steps": [(task, f"执行失败: {str(e)}")]}
