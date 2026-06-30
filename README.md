# Linux AIOps Agent

基于 LangChain + LangGraph 的 Linux 服务器智能运维 Agent 系统。

## 架构

```
接入层 → API + CLI
业务层 → AgentService / AIOpsService / KnowledgeService
服务层 → Provider / Retrieval / Tools / MCP
存储层 → Chroma + 知识库文档
```

## 快速开始

```bash
# 1. 安装
pip install -e ".[dev]"
cp .env.example .env   # 填入 API Key

# 2. 注入知识库
python scripts/ingest_knowledge.py

# 3. 启动 MCP 工具服务
make mcp-start

# 4. 启动 CLI
make cli
```

## 核心接口

| 接口 | 说明 |
|------|------|
| `POST /api/chat_stream` | 流式对话 (SSE) |
| `POST /api/aiops` | AIOps 诊断 (SSE) |
| `GET /api/health` | 健康检查 |
| `python cli.py` | 终端交互界面 |

## Tech Stack

- **LLM**: DeepSeek V4 Flash
- **Embedding**: DashScope text-embedding-v4
- **Vector DB**: Chroma
- **Agent**: LangGraph (ReAct + Plan-Execute-Replan)
- **Tools**: MCP (日志查询 / 系统状态 / 联网搜索)
