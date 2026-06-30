"""AIOps 服务 - Plan-Execute-Replan 诊断流程"""

from typing import AsyncGenerator, Dict, Any
from loguru import logger
from app.graphs.aiops_graph import build_aiops_graph
from app.nodes.state import PlanExecuteState


class AIOpsService:
    """运维诊断服务

    接收告警/任务描述，执行 Planner → Executor → Replanner 循环，
    通过 SSE 流式输出诊断过程和结果。
    """

    def __init__(self):
        self.graph = build_aiops_graph()
        logger.info("AIOpsService 初始化完成")

    async def execute(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"[{session_id}] AIOps 开始: {user_input[:60]}...")
        try:
            state = PlanExecuteState(input=user_input, plan=[], past_steps=[], response="")
            config = {"configurable": {"thread_id": session_id}}

            async for event in self.graph.astream(state, config=config, stream_mode="updates"):
                for node_name, output in event.items():
                    if node_name == "planner":
                        plan = output.get("plan", [])
                        yield {"type": "plan", "message": f"已制定 {len(plan)} 步计划", "plan": plan}
                    elif node_name == "executor":
                        past = output.get("past_steps", [])
                        if past:
                            step, _ = past[-1]
                            remaining = len(output.get("plan", []))
                            yield {"type": "step", "message": f"执行: {step[:60]}...", "remaining": remaining}
                    elif node_name == "replanner":
                        if output.get("response"):
                            yield {"type": "report", "message": "诊断完成", "report": output["response"]}

            yield {"type": "complete", "message": "AIOps 流程完成"}

        except Exception as e:
            logger.error(f"AIOps 执行失败: {e}")
            yield {"type": "error", "message": str(e)}


aiops_service = AIOpsService()
