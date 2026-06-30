#!/usr/bin/env python3
"""
Linux AIOps Agent - 终端 CLI 界面
"""

import asyncio
import signal
import sys
import threading
import queue
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from app.config import config
from app.services.agent_service import agent_service
from app.services.knowledge_service import knowledge_service
from app.services.log_watcher import log_watcher
from app.services.alert_manager import alert_manager
from app.mcp.manager import MCPManager
from app.services.log_simulator import log_simulator

VALID_COMMANDS = {"/exit", "/quit", "/clear", "/help", "/alerts"}
console = Console()

_exiting = False


def _cleanup_on_exit():
    """信号处理器 - 确保子进程被清理"""
    global _exiting
    if _exiting:
        return
    _exiting = True
    MCPManager.close_sync()
    print("\n[进程已清理]")
    sys.exit(0)


def print_banner():
    doc_count = knowledge_service.count_documents()
    banner = """\
    +------------------------------------------+
    |          Linux AIOps Agent                |
    |         主动运维 + 智能诊断                |
    +------------------------------------------+
    """
    console.print(banner, style="bold cyan", justify="center")

    info = Table.grid(padding=(0, 2))
    info.add_column()
    info.add_column()
    info.add_row("Version", config.app_version)
    info.add_row("Provider", "DeepSeek")
    info.add_row("Model", config.deepseek_model)
    info.add_row("Knowledge", f"{doc_count} chunks")
    console.print(info, style="dim")
    print()
    console.print(" 日志监控已启动 | 发现异常会自动推送")
    print()


def render_alert_card(alert):
    severity_colors = {"critical": "bold red", "warning": "yellow"}
    color = severity_colors.get(alert.severity, "white")
    title = f"[{alert.severity.upper()}] {alert.rule_name}"
    content = alert.raw_log
    if alert.diagnosis:
        content += f"\n\n[bold]分析:[/]\n{alert.diagnosis[:600]}"
    else:
        content += "\n\n[dim]分析中...[/]"
    console.print()
    console.print(Panel(content, title=title, title_align="left", border_style=color, box=box.HEAVY))
    print()


async def show_pending_alerts() -> bool:
    alerts = alert_manager.get_pending()
    for alert in alerts:
        render_alert_card(alert)
    return len(alerts) > 0


async def ask_agent(question: str) -> str:
    answer = ""
    async for event in agent_service.query_stream(question, session_id="cli"):
        if event["type"] == "content":
            answer += event["data"]
            sys.stdout.write(event["data"])
            sys.stdout.flush()
        elif event["type"] == "error":
            console.print(f"\n[bold red]ERROR: {event['data']}[/]")
    return answer


async def handle_command(cmd: str) -> str:
    if cmd in ("/exit", "/quit", "quit"):
        print("Bye!")
        await asyncio.gather(log_watcher.stop(), log_simulator.stop(), MCPManager.close(), return_exceptions=True)
        return "exit"

    if cmd in ("/clear", "clear"):
        console.clear()
        print_banner()
        return "handled"

    if cmd == "/help":
        console.print(Panel(
            "Commands:\n"
            "  /exit, /quit    quit\n"
            "  /clear, clear   clear\n"
            "  /help           help\n"
            "  /alerts         show pending alerts\n\n"
            "Type any Linux ops question.",
            title="Help", border_style="green", box=box.ROUNDED,
        ))
        return "handled"

    if cmd == "/alerts":
        await show_pending_alerts()
        return "handled"

    return "ignore"


async def main():
    signal.signal(signal.SIGINT, lambda s, f: _cleanup_on_exit())
    signal.signal(signal.SIGTERM, lambda s, f: _cleanup_on_exit())

    await log_simulator.start()
    await log_watcher.start()
    await agent_service._initialize()
    print_banner()

    # 用线程读取输入，不阻塞主循环
    input_queue = queue.Queue()
    input_lock = threading.Lock()

    def reader():
        while True:
            try:
                line = sys.stdin.readline()
                if line:
                    with input_lock:
                        input_queue.put(line.strip())
            except:
                break

    threading.Thread(target=reader, daemon=True).start()

    try:
        console.print("[bold cyan]> [/]", end="")
        sys.stdout.flush()

        while True:
            # 检查告警（后台自动弹出）
            if await show_pending_alerts():
                # 告警弹出后重新显示提示符
                console.print("[bold cyan]> [/]", end="")
                sys.stdout.flush()

            # 检查用户输入（不阻塞）
            user_input = None
            with input_lock:
                if not input_queue.empty():
                    user_input = input_queue.get()

            if user_input is None:
                await asyncio.sleep(0.5)
                continue

            raw = user_input.strip()
            if not raw:
                console.print("[bold cyan]> [/]", end="")
                sys.stdout.flush()
                continue

            result = await handle_command(raw)
            if result == "exit":
                break
            if result == "handled":
                console.print("[bold cyan]> [/]", end="")
                sys.stdout.flush()
                continue

            console.print(Panel(raw, title="You", title_align="left", border_style="green", box=box.ROUNDED))
            console.print("[bold blue]Agent:[/]")
            answer = await ask_agent(raw)
            if answer:
                print()
            console.print("[bold cyan]> [/]", end="")
            sys.stdout.flush()

    except (EOFError, KeyboardInterrupt):
        print("\nBye!")
    finally:
        await asyncio.gather(log_watcher.stop(), log_simulator.stop(), MCPManager.close(), return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
