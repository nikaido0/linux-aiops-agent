"""Agent 工具注册"""

from .knowledge_tool import retrieve_knowledge
from .time_tool import get_current_time

DEFAULT_LOCAL_TOOLS = [retrieve_knowledge, get_current_time]
