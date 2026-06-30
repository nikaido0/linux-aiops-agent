"""Agent 服务 - ReAct 对话 Agent"""

from typing import Any, AsyncGenerator, Dict
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger
from app.providers.registry import ProviderRegistry
from app.tools import DEFAULT_LOCAL_TOOLS
from app.mcp.manager import MCPManager
from app.services.knowledge_service import knowledge_service
from app.services.prompt_builder import prompt_builder
from app.services.context_manager import context_manager


class AgentService:
    """ReAct 对话 Agent"""

    def __init__(self):
        self.checkpointer = MemorySaver()
        self.agent = None
        self._initialized = False
        logger.info("AgentService 初始化完成")

    async def _initialize(self):
        if self._initialized:
            return
        llm = ProviderRegistry.get_llm(temperature=0.7)
        mcp_tools = await MCPManager.get_tools()
        self.all_tools = list(DEFAULT_LOCAL_TOOLS) + mcp_tools
        self.agent = create_react_agent(llm, tools=self.all_tools, checkpointer=self.checkpointer)
        self._initialized = True
        logger.info(f"Agent 初始化完成, 共 {len(self.all_tools)} 个工具")

    async def query_stream(self, question: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            await self._initialize()
            config = {"configurable": {"thread_id": session_id}}

            # 1. 检索知识库
            context = knowledge_service.search(question)

            # 2. PromptBuilder 构建纯角色 SystemMessage（稳定不变）
            sys_msg = prompt_builder.build()

            # 3. 获取历史消息
            try:
                state = self.checkpointer.get(config)
                if state:
                    checkpoint = state[0] if isinstance(state, tuple) else state
                    existing_messages = checkpoint.get("channel_values", {}).get("messages", [])
                else:
                    existing_messages = []
            except Exception:
                existing_messages = []

            # 4. ContextManager 组装上下文（历史裁剪 + token 预算 + 消息拼接）
            messages = context_manager.assemble(
                sys_msg=sys_msg,
                history=existing_messages,
                knowledge=context,
                tools=self.all_tools,
                question=question,
            )

            # 5. 流式调用 Agent
            async for token, metadata in self.agent.astream(
                {"messages": messages}, config=config, stream_mode="messages"
            ):
                msg_type = type(token).__name__
                if msg_type in ("AIMessage", "AIMessageChunk"):
                    content = getattr(token, "content", "")
                    if content:
                        yield {"type": "content", "data": content}

            yield {"type": "complete"}

        except Exception as e:
            logger.error(f"Agent 流式查询失败: {e}")
            yield {"type": "error", "data": str(e)}


agent_service = AgentService()
