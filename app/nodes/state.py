"""Plan-Execute-Replan 状态定义"""

from typing import List, TypedDict, Annotated
import operator


class PlanExecuteState(TypedDict):
    """Plan-Execute-Replan 工作流状态"""
    input: str                                     # 用户任务/告警描述
    plan: List[str]                                # 待执行的步骤列表
    past_steps: Annotated[List[tuple], operator.add]  # 已执行步骤历史
    response: str                                  # 最终响应
