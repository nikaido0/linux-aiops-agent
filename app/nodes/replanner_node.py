"""Replanner 节点 - 评估执行结果，决定继续/调整/结束

三条决策路径:
  - respond:  信息足够，生成最终响应（最高优先级）
  - continue: 继续执行当前计划
  - replan:   调整剩余计划（谨慎使用，5 步后禁止）
"""

from textwrap import dedent
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from app.providers.registry import ProviderRegistry
from .state import PlanExecuteState

MAX_STEPS = 8


async def replanner_node(state: PlanExecuteState) -> Dict[str, Any]:
    """评估结果并决定下一步"""
    plan = state.get("plan", [])
    past_steps = state.get("past_steps", [])
    exec_count = len(past_steps)
    logger.info(f"=== Replanner: 已执行 {exec_count} 步, 剩余 {len(plan)} 步 ===")

    # 强制结束条件
    if exec_count >= MAX_STEPS:
        return await _generate_response(state)

    if not plan:
        return await _generate_response(state)

    # 让 LLM 做决策
    llm = ProviderRegistry.get_llm(temperature=0)
    steps_summary = "\n".join([
        f"步骤{i+1}: {step[:80]}...\n结果: {result[:150]}..."
        for i, (step, result) in enumerate(past_steps)
    ])

    prompt = ChatPromptTemplate.from_messages([
        ("system", dedent("""\
            根据已执行步骤决定下一步行动。选择以下三种之一:

            respond - 信息足够，生成最终响应【优先】
            continue - 继续执行当前计划
            replan - 需要调整计划【谨慎，5步后禁止】

            决策原则:
            - 已执行 >= 3 步且信息充分 → respond
            - 已执行 >= 5 步 → 必须 respond
            - 总步骤数上限 8 步
            - 输出格式: 决策: <respond/continue/replan>
        """).strip()),
        ("user", "原始任务: {input}\n\n已执行:\n{steps}\n\n剩余计划: {plan}\n\n决策:"),
    ])

    result = await llm.ainvoke(prompt.format(
        input=state.get("input", ""),
        steps=steps_summary,
        plan="\n".join(plan),
    ))

    decision = result.content.strip().lower()
    logger.info(f"Replanner 决策: {decision[:50]}")

    if "respond" in decision:
        return await _generate_response(state)
    elif "replan" in decision and exec_count < 5:
        # 生成新的计划
        new_plan = await _replan(state)
        return {"plan": new_plan[:len(plan)]} if new_plan else {}

    return {}


async def _generate_response(state: PlanExecuteState) -> Dict[str, Any]:
    """生成最终响应"""
    llm = ProviderRegistry.get_llm(temperature=0)
    past_steps = state.get("past_steps", [])
    history = "\n\n".join([
        f"## 步骤{i+1}: {step}\n结果:\n{result}"
        for i, (step, result) in enumerate(past_steps)
    ])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "根据运维任务和执行结果，生成结构清晰、基于数据的最终响应，用 Markdown 格式。"),
        ("user", "原始任务: {input}\n\n执行记录:\n{history}\n\n请生成最终响应:"),
    ])

    result = await llm.ainvoke(prompt.format(input=state.get("input", ""), history=history))
    response = result.content if hasattr(result, "content") else str(result)
    return {"response": response, "plan": []}


async def _replan(state: PlanExecuteState) -> list:
    """重新规划剩余步骤"""
    llm = ProviderRegistry.get_llm(temperature=0)
    past = state.get("past_steps", [])
    history = "\n".join([f"- {s}: {r[:100]}" for s, r in past])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "根据已执行结果，制定剩余步骤的新计划，每行一个步骤。"),
        ("user", "原始: {input}\n已执行:\n{past}\n\n新计划:"),
    ])

    result = await llm.ainvoke(prompt.format(input=state.get("input", ""), past=history))
    return [l.strip() for l in result.content.strip().split("\n") if l.strip() and len(l.strip()) > 5][:5]
