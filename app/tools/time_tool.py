"""当前时间工具 - Agent 获取当前时间戳"""

from datetime import datetime
from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """获取当前时间

    当需要知道当前日期或时间时使用此工具，返回格式: YYYY-MM-DD HH:MM:SS
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
