"""ContextManager - Agent 上下文调度器

职责:
  1. 历史消息管理 — 保留/裁剪对话历史
  2. Token 预算控制 — 估算 token，超限自动裁剪
  3. 上下文结构组装 — 决定最终喂给 LLM 的消息结构
  4. Tool Result 注入策略 — 控制 tool result 的保留窗口

用法:
    ctx = ContextManager(max_tokens=32000, kept_rounds=3)
    messages = ctx.assemble(
        sys_msg=system_message,
        history=existing_messages,
        knowledge="知识库检索结果",
        tools=tool_list,
        question="用户问题",
    )
"""

from datetime import datetime
from typing import List, Optional, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage

# ──────────────────────────────────────────────
# Token 估算
# ──────────────────────────────────────────────

_HAS_TIKTOKEN = False
_TOKENIZER = None

try:
    import tiktoken
    _TOKENIZER = tiktoken.get_encoding("cl100k_base")
    _HAS_TIKTOKEN = True
except ImportError:
    pass


def estimate_tokens(text: str) -> int:
    """估算文本 token 数

    优先用 tiktoken（准确），回退到字符估算（约 4 字符 / token）。
    """
    if _TOKENIZER:
        return len(_TOKENIZER.encode(text))
    # 中文 + 英文混合，平均约 3-5 字符/token，取 4
    return len(text) // 4 + 1


def estimate_message_tokens(msg: BaseMessage) -> int:
    """估算单条消息的 token 数"""
    n = estimate_tokens(msg.content if hasattr(msg, "content") and msg.content else "")
    # 消息类型的 overhead（role 标识等）
    n += 4
    return n


def estimate_messages_tokens(messages: List[BaseMessage]) -> int:
    """估算一组消息的总 token 数"""
    return sum(estimate_message_tokens(m) for m in messages)


# ──────────────────────────────────────────────
# ContextManager
# ──────────────────────────────────────────────

class ContextManager:
    """Agent 上下文调度器"""

    def __init__(
        self,
        max_tokens: int = 32000,
        kept_rounds: int = 3,
        tool_result_window: int = 2,
    ):
        """
        Args:
            max_tokens: LLM 上下文窗口上限（预留 buffer）
            kept_rounds: 保留的完整对话轮数
            tool_result_window: 保留的最近 tool result 轮数
        """
        self.max_tokens = max_tokens
        self.kept_rounds = kept_rounds
        self.tool_result_window = tool_result_window

    # ── Token 估算 ──

    def estimate_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    def estimate_messages_tokens(self, messages: List[BaseMessage]) -> int:
        return estimate_messages_tokens(messages)

    # ── 历史消息管理 ──

    def trim_history(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """裁剪消息历史

        策略:
          1. 保留第一条 SystemMessage
          2. 保留最近 N 轮完整的 User/AI/Tool 消息
          3. 在 token 超限时，从旧到新丢弃 ToolMessage
        """
        if not messages:
            return messages

        # 分离 SystemMessage 和其余消息
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        others = [m for m in messages if not isinstance(m, SystemMessage)]

        system_msg = system_msgs[0] if system_msgs else None

        if not others:
            return [system_msg] if system_msg else []

        # 从尾部向前取 KEPT_ROUNDS 轮
        # 一轮 = User → AI(+Tool...)
        rounds = []
        current_round: List[BaseMessage] = []
        for msg in reversed(others):
            current_round.append(msg)
            if isinstance(msg, HumanMessage):
                # 遇到 HumanMessage 说明一轮结束
                current_round.reverse()
                rounds.append(current_round)
                current_round = []
                if len(rounds) >= self.kept_rounds:
                    break

        if current_round:
            current_round.reverse()
            rounds.append(current_round)

        # 展平，保持时间顺序
        kept = [m for r in reversed(rounds) for m in r]

        # 检查 token 预算，从最旧开始丢弃 ToolMessage
        result = ([system_msg] if system_msg else []) + kept
        while estimate_messages_tokens(result) > self.max_tokens:
            # 找到最旧的 ToolMessage 丢弃
            dropped = False
            for i, m in enumerate(result):
                if isinstance(m, ToolMessage):
                    result.pop(i)
                    dropped = True
                    break
            if not dropped:
                # 没有 ToolMessage 可丢，从旧到新丢弃 AI/User
                for i, m in enumerate(result):
                    if isinstance(m, (AIMessage, HumanMessage)):
                        result.pop(i)
                        dropped = True
                        break
            if not dropped:
                break  # 不能再丢了

        return result

    # ── 上下文结构组装 ──

    def assemble(
        self,
        *,
        sys_msg: SystemMessage,
        history: List[BaseMessage],
        knowledge: str,
        tools: Optional[List[Any]] = None,
        question: str,
    ) -> List[BaseMessage]:
        """组装最终的消息列表

        结构:
            SystemMessage(纯角色定义)
            History(裁剪后的历史)
            HumanMessage(知识库 + 工具列表 + 问题)
        """
        # 1. 裁剪历史
        history = self.trim_history(history)

        # 2. 构建 HumanMessage
        tool_text = ""
        if tools:
            lines = []
            for t in tools:
                name = getattr(t, "name", str(t))
                desc = getattr(t, "description", "")[:100]
                lines.append(f"- {name}: {desc}")
            tool_text = "\n".join(lines) if lines else "暂无专用工具"
        else:
            tool_text = "暂无专用工具"

        context_block = (
            f"## 当前时间\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"## 知识库参考\n{knowledge or '本次未检索知识库'}\n\n"
            f"## 可用工具\n{tool_text}\n\n"
            f"## 用户问题\n{question}"
        )

        # 3. 组装
        messages: List[BaseMessage] = [sys_msg]
        for msg in history:
            if isinstance(msg, SystemMessage):
                continue  # 替换旧的
            messages.append(msg)
        messages.append(HumanMessage(content=context_block))

        return messages

    def summary(self, messages: List[BaseMessage]) -> dict:
        """调试用：输出消息列表的摘要"""
        total = estimate_messages_tokens(messages)
        info = {
            "total_tokens": total,
            "max_tokens": self.max_tokens,
            "within_budget": total <= self.max_tokens,
            "count": len(messages),
            "breakdown": [],
        }
        for m in messages:
            t = type(m).__name__
            c = estimate_message_tokens(m)
            preview = (m.content[:60] + "...") if hasattr(m, "content") and m.content else ""
            info["breakdown"].append({"type": t, "tokens": c, "preview": preview})
        return info


context_manager = ContextManager()
