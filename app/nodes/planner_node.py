"""Planner 节点 - 将运维任务分解为执行计划

根据用户输入的告警/任务描述，结合知识库经验和可用工具，生成结构化的执行步骤。

流程:
  1. 查询知识库，获取相关运维经验文档
  2. 获取所有可用工具列表（本地 + MCP）
  3. LLM 生成步骤计划 (Plan.steps)
"""

from textwrap import dedent
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from app.providers.registry import ProviderRegistry
from app.services.knowledge_service import knowledge_service
from app.tools import DEFAULT_LOCAL_TOOLS
from app.mcp.manager import MCPManager
from .state import PlanExecuteState


def _format_tools(tools: list) -> str:
    return "\n".join([f"- {t.name}: {t.description}" for t in tools if hasattr(t, "name")])


async def planner_node(state: PlanExecuteState) -> Dict[str, Any]:
    """Planner: 生成执行计划"""
    logger.info("=== Planner: 制定执行计划 ===")
    input_text = state.get("input", "")

    try:
        # 1. 检索知识库经验
        experience = knowledge_service.search(input_text)
        exp_ctx = f"\n## 参考经验\n{experience}\n" if experience else ""

        # 2. 获取工具列表
        local_tools = list(DEFAULT_LOCAL_TOOLS)
        mcp_tools = await MCPManager.get_tools()
        all_tools = local_tools + mcp_tools
        tools_desc = _format_tools(all_tools)

        # 3. 生成计划
        prompt = ChatPromptTemplate.from_messages([
            ("system", dedent("""\
                你是一个 Linux 运维专家规划者。将复杂的运维任务分解为可执行的步骤。

                可用工具:
                {tools}

                参考经验文档:
                {experience}

                要求:
                - 步骤之间要有清晰的依赖关系
                - 每个步骤需明确使用哪些工具
                - 步骤描述要具体、可操作
                示例:
                步骤1: 使用 get_current_time 获取当前时间
                步骤2: 使用 query_journalctl 查询最近系统错误日志
                步骤3: 使用 cpu_info 查看 CPU 使用情况
            """).strip()),
            ("user", "{input}"),
        ])

        llm = ProviderRegistry.get_llm(temperature=0)
        result = await llm.ainvoke(prompt.format(tools=tools_desc, experience=exp_ctx, input=input_text))

        # 解析 LLM 输出为步骤列表
        steps = _parse_steps(result.content)
        logger.info(f"计划已生成: {len(steps)} 个步骤")

        return {"plan": steps or ["收集相关信息", "分析数据", "生成报告"]}

    except Exception as e:
        logger.error(f"生成计划失败: {e}")
        return {"plan": ["收集相关信息", "分析问题", "生成报告"]}


def _parse_steps(text: str) -> List[str]:
    """从 LLM 输出中提取步骤列表"""
    steps = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 匹配 "步骤1: ", "1. ", "- " 等格式
        cleaned = line
        for prefix in ["步骤", "Step", "step"]:
            if prefix in line[:10]:
                cleaned = line.split(":", 1)[-1] if ":" in line else line
                break
        if cleaned.startswith("- "):
            cleaned = cleaned[2:]
        # 去掉数字前缀 "1. ", "2. "
        parts = cleaned.split(". ", 1)
        if parts[0].strip().isdigit() and len(parts) > 1:
            cleaned = parts[1]

        if cleaned and len(cleaned) > 5:
            steps.append(cleaned.strip())

    return steps[:10]
