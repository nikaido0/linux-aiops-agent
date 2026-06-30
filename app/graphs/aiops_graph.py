"""AIOps Plan-Execute-Replan 状态图"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger
from app.nodes.state import PlanExecuteState
from app.nodes.planner_node import planner_node
from app.nodes.executor_node import executor_node
from app.nodes.replanner_node import replanner_node


def build_aiops_graph():
    """构建 Plan-Execute-Replan 状态图

    流程:
        planner (制定计划) → executor (执行步骤) → replanner (评估)
        ↑_________________ continue _________________|
        |_________________ respond → END
    """
    workflow = StateGraph(PlanExecuteState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("replanner", replanner_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "replanner")

    def should_continue(state: PlanExecuteState) -> str:
        if state.get("response"):
            return END
        if state.get("plan"):
            return "executor"
        return END

    workflow.add_conditional_edges("replanner", should_continue, {
        "executor": "executor",
        END: END,
    })

    graph = workflow.compile(checkpointer=MemorySaver())
    logger.info("AIOps 状态图构建完成")
    return graph
