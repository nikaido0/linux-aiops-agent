# Linux AIOps Agent

基于 LangChain + LangGraph 的 Linux 服务器智能运维 Agent 系统。

## 项目介绍

面向实验室 Linux 服务器运维场景，整合知识库检索、主动日志监控与运维工具调用，实现 Linux 常见运维问题自动问答、实时异常检测及故障诊断建议生成。

## 技术栈

| 组件 | 选型 |
|------|------|
| 框架 | FastAPI + SSE 流式输出 |
| LLM | DeepSeek V4 Flash (OpenAI 兼容 API) |
| Embedding | DashScope text-embedding-v4 (1024 dim) |
| 向量库 | Chroma (嵌入式，无需 Docker) |
| Agent | LangGraph (ReAct + Plan-Execute-Replan) |
| 工具协议 | MCP (Model Context Protocol) |
| CLI | Rich 终端交互界面 |

## 架构

```
┌──────────────────────────────────────────────────────┐
│  CLI / API 接入层                                     │
│  cli.py  │  POST /api/chat_stream  │  POST /api/aiops │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│  业务层                                              │
│  AgentService (ReAct)  │  AIOpsService (Plan-Exec)   │
│  PromptBuilder          │  MemorySaver (3轮消息修剪)  │
│  LogWatcher (主动监控)  │  AlertManager (告警推送)    │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────┼───────────────────────────────────┐
│  服务层           │                                   │
│  ┌──────────────┐│┌────────────┐  ┌────────────────┐ │
│  │ Hybrid RAG  │││  Provider  │  │  MCP 工具集    │ │
│  │ BM25+Vec+RRF│││  Registry  │  │  log/linux/search│ │
│  │ +Reranker   │││  DeepSeek  │  └────────────────┘ │
│  └──────┬───────┘│└────────────┘                     │
└─────────┼────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────┐
│  存储层                                              │
│  Chroma (90 chunks)  │  knowledge/linux/ (15 篇文档) │
│  logs/simulated/      │  BM25 索引 (内存)            │
└──────────────────────────────────────────────────────┘
```

## 核心功能

### 1. AI Agent 架构
- 基于 LangGraph 实现 ReAct 对话 Agent 和 Plan-Execute-Replan 诊断 Agent
- 多轮对话上下文的 PromptBuilder + 消息修剪机制
- MCP 工具协议集成日志查询、系统状态、搜索能力

### 2. Hybrid RAG 知识库
- BM25 关键词检索 + Vector 语义检索 + RRF 融合排序 + Reranker 精排
- 15 篇 Linux 运维知识库文档，90 个语义分片
- 100 条测试集评估: HitRate@3 = 85%, HitRate@5 = 87%
- Hybrid Search 相比纯向量检索提升 +4%

### 3. 主动日志监控与告警
- LogWatcher 后台线程增量轮询 journalctl
- 规则引擎 (18 条规则) 过滤噪声，只关注真正的异常
- 命中异常自动触发 RAG 检索 + LLM 诊断分析
- CLI 端自动推送告警卡片，无需手动查询

### 4. LLM 问答质量
- 关键词覆盖率 93.3% (20 条采样)
- 知识库 + 工具调用双重验证回答准确性
- 平均 LLM 响应延迟 8.1s

## 快速开始

```bash
# 1. 安装依赖
pip install -e ".[dev]"

# 2. 配置 API Key
cp .env.example .env
# 填入 DASHSCOPE_API_KEY 和 DEEPSEEK_API_KEY

# 3. 注入知识库
python scripts/ingest_knowledge.py

# 4. 启动 CLI
python cli.py
```

## 评估结果

```text
RAG Hit Rate (100 queries):
  @K=1:  76.0%  (202ms)
  @K=3:  85.0%  (193ms)
  @K=5:  87.0%  (192ms)
  @K=10: 92.0%  (203ms)

Hybrid Search vs Pure Vector:
  Pure Vector:   87.0%
  Hybrid Search: 91.0%  (+4.0%)

LLM Answer Quality (20 samples):
  Keyword Coverage: 93.3%
  Avg Latency:      8.1s
```

## 项目结构

```
linux-aiops-agent/
├── app/
│   ├── api/              # FastAPI 路由 (health/chat/aiops)
│   ├── providers/        # DeepSeek Provider + Registry
│   ├── retrieval/        # Hybrid Search (BM25+Vec+RRF+Reranker)
│   ├── services/         # Agent/AIOps/Knowledge/PromptBuilder/LogWatcher
│   ├── graphs/           # AIOps LangGraph 状态图
│   ├── nodes/            # Planner/Executor/Replanner
│   ├── tools/            # 本地工具 (knowledge/time)
│   └── mcp/              # MCP 客户端管理器
├── mcp_servers/          # MCP 工具 (日志/系统状态/搜索)
├── knowledge/linux/      # 15 篇运维知识库文档
├── scripts/evaluation/   # 100 条测试集 + 评估框架
├── prompts/              # 系统提示模板
├── cli.py                # Rich 终端界面
└── tests/                # 测试
```
