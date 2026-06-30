"""Agent 服务 - ReAct 对话 Agent"""

from typing import Any, AsyncGenerator, Dict, List
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, RemoveMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from loguru import logger
from app.providers.registry import ProviderRegistry
from app.tools import DEFAULT_LOCAL_TOOLS
from app.mcp.manager import MCPManager
from app.services.knowledge_service import knowledge_service
from app.services.prompt_builder import prompt_builder

# 保留最近 N 轮对话（一对 User + AI 算一轮）
KEPT_ROUNDS = 3


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

    def _trim_history(self, messages: List) -> List:
        """修剪消息历史，只保留：
        1. 第一条消息（最新构建的 SystemMessage）
        2. 最近 KEPT_ROUNDS 轮对话
        """
        if len(messages) <= KEPT_ROUNDS * 2 + 1:
            return messages

        # 第一条是当前轮次的 SystemMessage（已含最新 RAG 上下文）
        system_msg = messages[0]

        # 取最近 KEPT_ROUNDS 轮（每轮 1 条 User + 1 条 AI = 2 条）
        recent = messages[-(KEPT_ROUNDS * 2):]

        # 检查 recent 的第一条是否是 User 消息（确保配对完整）
        if recent and isinstance(recent[0], AIMessage):
            # 如果以 AI 消息开头，多保留一条前面的 User 消息
            if len(messages) > KEPT_ROUNDS * 2 + 1:
                recent = messages[-(KEPT_ROUNDS * 2 + 1):]

        trimmed = [system_msg] + recent
        logger.info(f"修剪消息: {len(messages)} -> {len(trimmed)} 条")
        return trimmed

    async def query_stream(self, question: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            await self._initialize()
            config = {"configurable": {"thread_id": session_id}}

            # 1. 检索知识库
            context = knowledge_service.search(question)

            # 2. PromptBuilder 构建本轮 SystemMessage
            sys_msg = prompt_builder.build(
                knowledge_context=context,
                tools=self.all_tools,
            )

            # 3. 获取历史消息并修剪
            try:
                state = self.checkpointer.get(config)
                if state:
                    checkpoint = state[0] if isinstance(state, tuple) else state
                    existing_messages = checkpoint.get("channel_values", {}).get("messages", [])
                    existing_messages = self._trim_history(existing_messages)
                else:
                    existing_messages = []
            except Exception:
                existing_messages = []

            # 4. 构建本轮消息列表
            #    替换旧的 SystemMessage，保留修剪后的历史 + 新问题
            messages = [sys_msg]
            for msg in existing_messages:
                if isinstance(msg, SystemMessage):
                    continue  # 替换旧 system message
                if isinstance(msg, (HumanMessage, AIMessage)):
                    messages.append(msg)

            messages.append(HumanMessage(content=question))

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
