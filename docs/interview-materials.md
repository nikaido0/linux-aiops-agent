# Linux AIOps Agent 面试备考材料

> 面试官视角：15 年经验大厂技术面试官模拟
> 目标级别：P6/P7（高级工程师/专家）

---

# 第一部分：项目介绍

## 30 秒版本

我最近做了一个 Linux 智能运维 Agent 系统，基于 LangChain 和 LangGraph。核心思路是让 AI 能自动排查服务器故障——它有一个 Hybrid RAG 知识库，15 篇运维文档 90 个分片，HitRate@3 能达到 85%；还有一个 Log Watcher 能主动监控系统日志，发现 OOM、磁盘满这些异常后自动检索知识库生成诊断建议。整个系统通过 MCP 协议对接了日志查询、系统状态采集等工具，Agent 可以自主调用。技术栈主要是 DeepSeek V4 Flash、Chroma 向量库、FastAPI 做 SSE 流式输出。

## 1 分钟版本

这个项目面向实验室 Linux 服务器运维场景，目标是减少运维人员重复排查的时间。

背景是实验室经常出现 OOM、磁盘满、服务宕机这类问题，每次都要人工看日志、查文档、写命令，费时费力。我就想能不能用 Agent 把这些重复劳动自动化。

整体架构分四层：接入层（CLI/API）、业务层（ReAct Agent 和 Plan-Execute-Replan 诊断流程）、服务层（Hybrid RAG 检索、MCP 工具集、Provider 管理）、存储层（Chroma 向量库加 BM25 索引）。

技术上的几个亮点：一是 Hybrid Search，用 BM25 加向量检索加 RRF 融合，在 100 条测试集上达到 85% 的 HitRate@3；二是主动日志监控，Log Watcher 后台轮询日志，规则引擎过滤后自动触发 RAG 加 LLM 分析推告警；三是 Provider 抽象，把 DeepSeek 封装成标准接口，换模型不用改业务代码。

最终的评估结果是 RAG 检索 85% 准确率，Hybrid Search 比纯向量提升 4 个百分点，LLM 回答关键词覆盖率达到 93%。

## 3 分钟版本

### 项目背景

实验室有十几台 Linux 服务器跑各种服务，经常出问题。每次出问题都是同样的套路：看日志、查文档、敲命令。这些重复劳动其实有很强的规律性——OOM 就那么几种原因，磁盘满就那么几种处理方式。我就想能不能做一个 AI Agent，把这些标准化排查流程自动化。

### 为什么做

三个原因：一是效率，人工排查一次平均 20 分钟，Agent 能做到秒级响应；二是知识沉淀，之前出过的问题和处理方案散落在各个人的脑袋里，没有一个统一的知识库；三是 7x24，人不会半夜爬起来看告警，但 Agent 可以。

### 整体架构

四层架构。接入层是 CLI（Rich 终端）和三个 API（chat_stream、aiops、health）。业务层两个 Agent：ReAct 做对话问答，Plan-Execute-Replan 做复杂诊断。服务层包含 Hybrid RAG（BM25+Vector+RRF+Reranker）、Provider Registry（管理 DeepSeek）、MCP 工具集。存储层是 Chroma 加 BM25 内存索引。

### 核心技术

第一块是 RAG，15 篇文档切 90 个分片，BM25 做关键词召回、Vector 做语义召回、RRF 融合排序、Reranker 精排。第二块是 Agent 编排，对话用 LangGraph 的 create_react_agent 做 ReAct 循环，诊断用自定义的 StateGraph 做 Plan-Execute-Replan。第三块是主动监控，LogWatcher 后台轮询 journalctl，规则引擎 18 条规则过滤，命中后自动检索知识库加 LLM 分析。

### 我的职责

我一个人完成了全部工作：架构设计、技术选型、代码实现、知识库构建、评估测试。从立项到完成大概用了两周。

### 难点和解决方案

第一个难点是检索精度。纯向量检索在关键词类查询（比如 OOM、SIGKILL）上表现不够好。解决方案是 Hybrid Search，用 BM25 做关键词兜底，保持召回率。第二个难点是 LLM 幻觉，回答容易脱离知识库编造。解决方案是 PromptBuilder 把 RAG 上下文拼到 System Message 里，并配合工具调用让回答基于实际数据。第三个难点是日志里的噪声太多，不可能每条都交给 LLM。解决方案是规则引擎前置过滤，只有匹配预定义规则（OOM、磁盘满、内核 Panic 等）才触发分析。

### 最终效果

100 条运维测试集上 RAG HitRate@3 达到 85%，Hybrid Search 相比纯向量提升 4 个百分点，LLM 回答关键词覆盖率 93%。整个系统在 Windows 开发环境可完整运行，生产环境只需部署到 Linux 服务器即可接入真实日志。

---

# 第二部分：项目架构讲解

## 整体架构

四层架构是我在初期设计时就确定的。为什么分四层？因为每一层的职责和变化频率不同。

接入层负责协议转换，业务层负责流程编排，服务层提供原子能力，存储层管理持久化。这样做的好处是每层可以独立演进——比如接入层加个 WebSocket 接口不需要改业务逻辑，服务层加个新工具不需要改接入层。

另一种方案是两层架构（API 直连 Service），简单是简单，但 Provider 切换、工具扩展、检索策略调整都会牵一发而动全身。四层架构虽然前期多了些接口定义工作，但后期的扩展成本低很多。

## 各模块职责

- **api/**：路由注册，参数校验，SSE 流式响应。只做协议转换，不包含业务逻辑。
- **providers/**：LLM 和 Embedding 的抽象。核心是 ProviderRegistry，一个注册中心模式的工厂。
- **retrieval/**：检索层。HybridRetriever 组合了 ChromaStore、DocumentSplitter、Reranker，对外只暴露 ingest 和 search。
- **services/**：业务编排。AgentService 包装了 LangGraph 的 ReAct Agent，AIOpsService 包装了 Plan-Execute-Replan 状态图，KnowledgeService 包装了检索流程。
- **mcp/**：MCP 工具管理。MCPManager 是全局单例，管理子进程生命周期和客户端连接。
- **graphs/ + nodes/**：LangGraph 的状态图定义和节点实现。
- **tools/**：本地 Agent 工具，不需要 MCP 的简单能力。

为什么 services 要单独成层而不是直接写在 api 里？因为 api 里的路由 handler 应该是很薄的一层，只做请求解析和响应序列化。业务逻辑放到 services 里，方便测试也方便 CLI 复用。

## 数据流

用户输入 → CLI/API → AgentService._initialize() → MCPManager.get_tools() → ProviderRegistry.get_llm() → create_react_agent → astream → SSE/print

具体来说：用户输入先到 CLI，CLI 调用 AgentService.query_stream。这个方法内部先确保 Agent 初始化（加载 MCP 工具和 LLM），然后调用 knowledge_service.search 做 RAG 检索，然后 PromptBuilder 构建 SystemMessage，再拼接历史消息（经消息修剪），最后发给 LangGraph 的 ReAct Agent 流式执行。

## Agent 工作流程

对话场景走 ReAct。LangGraph 的 create_react_agent 本质是一个 while 循环：LLM 输出 → 如果是工具调用就执行工具 → 把结果喂回 LLM → 直到 LLM 直接输出文本回答。这个循环不需要我手动写，LangGraph 的 prebuilt agent 封装好了。

为什么不用自己写 while 循环？自己写要考虑的东西太多——什么时候停止、怎么处理工具调用异常、怎么流式输出。create_react_agent 把这些都处理好了，而且有 ToolNode 自动执行工具，异常会自动处理。

诊断场景走 Plan-Execute-Replan。三阶段：Planner 先生成步骤计划，Executor 一步步执行，Replanner 评估结果决定继续还是结束。这个流程是用 StateGraph 手写的，因为诊断场景的决策逻辑比对话复杂——需要判断信息够不够、要不要调整计划、什么时候强制结束。

## RAG 工作流程

用户问题进来，先走 BM25，把所有文档分片的关键词匹配一遍，取 Top30。同时走 Vector Search，用 Embedding 转向量去 Chroma 查 Top30。然后 RRF 把两个结果集按排名融合——同一个文档在两个结果集中都出现的话排名会显著提升。最后 Reranker 对融合结果做交叉编码器精排，取 Top5 输出。

这个流程的核心设计原则是"宽进严出"：BM25 和 Vector 各自用不同的角度召回，确保不遗漏；RRF 融合排序把两个角度的优势叠加；Reranker 最后卡质量关，用计算量大的交叉编码器只精排少量候选。

## Prompt 构建流程

PromptBuilder 每次请求前从固定模板 `prompts/system_prompt.md` 读取，然后替换三个占位符：`{tools}`（当前 Agent 可用的工具列表）、`{current_time}`（当前时间）、`{knowledge_context}`（本轮的 RAG 检索结果）。

为什么不在代码里硬编码 System Prompt？因为模板和代码分离后，改 Prompt 不用改代码，运维同事也能改。这在团队协作里很重要——很多时候调 Prompt 的不是开发，是算法或运营。

为什么每次请求都重建 SystemMessage 而不是复用同一个？因为 RAG 上下文每轮不同，工具列表也可能因为 MCP 连接状态而变化。如果复用旧的 SystemMessage，里面可能包含上一轮的检索结果，造成上下文污染。

## Memory 工作流程

用 LangGraph 的 MemorySaver，通过 thread_id 区分会话。每次调用传入同样的 session_id，LangGraph 自动把历史消息保存到内存字典里。

为什么不用 Redis 或数据库持久化？实验室场景不需要——CLI 退出后会话结束，历史丢就丢了。如果要做生产级的持久化，MemorySaver 可以替换为 PostgresSaver 或 RedisSaver，接口不变。

消息修剪策略：保留最新的 SystemMessage（含本轮 RAG 上下文），丢弃旧的 SystemMessage，保留最近 3 轮对话。为什么是 3 轮？因为运维对话通常每轮问题独立——上轮问 CPU，这轮问磁盘，保留 3 轮足够捕捉上下文关联，再多就浪费 token 了。

## Tool 调用流程

Agent 的 Tool 分两类：本地工具（Local Tool）和 MCP 工具。本地工具有 retrieve_knowledge 和 get_current_time，直接在进程内执行。MCP 工具通过 MCPManager 连接远程 MCP Server，走 HTTP 协议。

MCP 工具调用过程：Agent 决定调用 query_logs → LangGraph 的 ToolNode 自动拦截 → 调 MCPManager.get_tools() 获取 MCP 工具列表 → MultiServerMCPClient 把请求转发到 log_server:8003 → log_server 执行命令返回结果 → 结果回到 ToolNode → 喂回 LLM。

MCP 的好处是工具可以分布式部署——log_server 可以跑在需要查日志的机器上，linux_server 跑在目标服务器上，主 Agent 跑在另一台机器上。缺点是增加了网络延迟和部署复杂度。

## Provider 调用流程

ProviderRegistry.get_llm() → 从 _providers 字典里拿 "deepseek" 对应的 DeepSeekProvider → 调 create_llm() → 返回 ChatOpenAI 实例。

为什么用注册中心模式而不是直接 import ChatOpenAI？因为如果以后要加 Claude 或 Qwen，只需要注册一个新的 Provider，业务代码一行不用改。这个模式是从 Spring 的 IoC 容器借鉴来的。

缺点也很明显：多了一层间接调用，代码可读性稍微下降。但在项目里业务代码几十处调 LLM，如果用硬编码，换模型就得改几十处，维护成本远高于这个间接调用成本。

## LangGraph 执行流程

对话：create_react_agent(llm, tools, checkpointer) → astream(messages, config) → 内部自动执行 ReAct 循环 → yield (token, metadata)

诊断：StateGraph(PlanExecuteState) → add_node("planner") → add_node("executor") → add_node("replanner") → add_conditional_edges("replanner", should_continue) → compile() → astream(state)

StateGraph 的执行流程就是遍历节点和边。每次进入一个节点，执行节点函数，函数返回状态更新，LangGraph 合并更新，然后根据条件边决定下一跳。

---

# 第三部分：亮点总结

## 工程能力

- **完整的项目结构**：从配置管理到日志到异常处理，每个模块职责清晰，符合 Python 项目最佳实践
- **模块解耦**：Provider、Retrieval、Tool、MCP 各自独立，修改一个不影响其他
- **错误恢复**：MCP 连接失败自动降级到本地工具，Reranker 不可用跳过精排，Agent 工具调用失败不中断流程
- **配置管理**：Pydantic Settings 类型安全配置，环境变量驱动，.env.example 做模板

## 架构设计

- **四层架构**：接入、业务、服务、存储职责清晰，每层可独立演进
- **Provider Registry**：工厂模式 + 注册中心，支持多模型提供商切换
- **MCPManager**：全局单例 + 自动子进程管理，启动关闭自动化
- **PromptBuilder**：模板与代码分离，动态构建 SystemMessage

## 性能优化

- **增量日志检查**：维护 last_check 时间戳，每次只查新日志
- **消息修剪**：只保留最近 3 轮对话，控制 Token 消耗
- **并发 LLM 分析**：多条告警用 asyncio.gather 并行分析
- **RAG Top10→3**：宽召回精排序，平衡精度与延迟

## Prompt Engineering

- **动态 SystemMessage**：每轮重建，包含本轮 RAG 上下文和工具信息
- **结构化输出**：Planner/Replanner 用 Pydantic BaseModel 约束输出格式
- **知识库上下文优先**：SystemPrompt 中知识库在前，引导 LLM 优先基于检索内容回答

## RAG

- **Hybrid Search**：BM25 + Vector + RRF + Reranker 四段式检索
- **BM25**：关键词精确匹配，适合错误码/OOM/SIGKILL 等运维场景
- **Dense Retrieval**：DashScope text-embedding-v4 1024 维向量，语义匹配
- **RRF**：无需训练的融合排序算法，保持 BM25 和 Vector 的优势
- **Reranker**：CrossEncoder 精排，在 Top30 中挑 Top5

## 评价指标

- 100 条运维测试集 HitRate@3 = 85%
- Hybrid Search 相比纯向量提升 4%
- LLM 回答关键词覆盖率 93.3%
- RAG 平均检索延迟 192ms

---

# 第四部分：面试官问题（100+ 题）

## 一、项目背景（5 题）

1. 为什么要做这个项目？解决了什么实际问题？
2. 这个项目和你之前的工作有什么关系？
3. 这个项目做了多久？你一个人完成的吗？
4. 有没有真正部署到生产环境使用？
5. 这个项目目标用户是谁？他们怎么使用这个系统？

## 二、需求分析（5 题）

6. 为什么选实验室 Linux 运维这个场景？
7. 这个场景下最重要的能力是什么？
8. 为什么不做 Web UI 而是做了 CLI？
9. 需求和功能怎么确定优先级？
10. 你调研过哪些竞品？他们没做好什么？

## 三、架构设计（5 题）

11. 为什么分四层架构？不是两层或三层？
12. 如果重新设计架构，你会改动哪里？
13. 各个模块怎么通信的？有没有模块间依赖问题？
14. 为什么 services 要独立成层而不是直接写在 api 里？
15. 这个架构能支撑多大规模？

## 四、技术选型（5 题）

16. 为什么选 DeepSeek 不是 GPT？
17. 为什么选 Chroma 不是 Milvus、Weaviate、Qdrant？
18. 为什么选 LangGraph 不是 AutoGen、CrewAI、Semantic Kernel？
19. 为什么用 FastAPI 不用 Flask、Django？
20. 为什么用 SSE 不用 WebSocket？

## 五、Agent（5 题）

21. 你的 Agent 有几种？分别负责什么？
22. ReAct 的循环什么时候结束？会不会死循环？
23. Plan-Execute-Replan 最多执行几步？为什么？
24. Agent 工具调用失败怎么处理？
25. Agent 怎么知道该调用哪个工具？

## 六、LangGraph（5 题）

26. LangGraph 的 StateGraph 怎么工作的？
27. 为什么用 LangGraph 而不是自己写状态机？
28. LangGraph 的 MemorySaver 怎么实现多轮记忆的？
29. LangGraph 和 LangChain 什么关系？
30. 如果用 LangGraph 写一个多 Agent 系统怎么设计？

## 七、LangChain（5 题）

31. 项目里用了 LangChain 的哪些组件？
32. create_react_agent 内部怎么工作的？
33. 为什么 ToolNode 能自动执行工具调用？
34. LangChain 的 document 和 message 模型怎么设计的？
35. 不用 LangChain 你怎么实现同样功能？

## 八、Prompt（5 题）

36. PromptBuilder 为什么设计成独立的类？
37. SystemPrompt 为什么用模板文件而不是写在代码里？
38. 你的 Prompt 有没有调优过程？
39. 怎么防止 LLM 忽略知识库内容自己编？
40. 工具描述怎么写能让 LLM 更好理解？

## 九、Context Engineering（5 题）

41. 上下文窗口不够用了怎么办？
42. 消息修剪策略为什么是 3 轮？
43. 旧的 RAG 上下文会污染新的对话吗？怎么解决的？
44. 给 LLM 的上下文里包含什么信息？
45. 上下文太长会影响延迟，怎么balance？

## 十、Memory（5 题）

46. MemorySaver 存在内存里，进程重启就丢了怎么办？
47. 怎么扩展 MemorySaver 到持久化存储？
48. 不同 session 的消息会互相干扰吗？
49. 消息修剪时直接把历史删掉，会不会丢失关键信息？
50. 有没有考虑对历史做摘要压缩？

## 十一、RAG（5 题）

51. 为什么 RAG 对运维场景特别重要？
52. 15 篇文档 90 个分片怎么来的？
53. chunk_size 和 overlap 怎么确定的？
54. 文档更新了怎么办？需要重建索引吗？
55. RAG 检索失败（没找到相关内容）怎么处理？

## 十二、Hybrid Search（5 题）

56. 为什么 Hybrid Search 比纯向量检索好？
57. BM25 召回 Top30，Vector 也召回 Top30，标准是什么？
58. 有没有出现过 BM25 和 Vector 都召不到正确结果的情况？怎么处理？
59. Hybrid Search 延迟比纯向量高多少？
60. 如果只能选一种（BM25 或 Vector），你选哪个？

## 十三、BM25（5 题）

61. BM25 的原理是什么？和 TF-IDF 什么关系？
62. BM25 的分词器怎么实现的？为什么只用 \w+？
63. BM25 索引为什么存在内存里？数据量大怎么办？
64. BM25 对中文支持好吗？中文日志怎么分词？
65. BM25 的参数 k1 和 b 怎么调？

## 十四、Embedding（5 题）

66. 为什么选 text-embedding-v4？评估过其他模型吗？
67. 1024 维的向量检索效率怎么样？
68. Embedding 的 API 调用失败怎么办？
69. 同一个模型 embedding 的向量和 query 的向量能直接比吗？
70. 有没有考虑用本地的 embedding 模型降低成本？

## 十五、RRF（5 题）

71. RRF 的原理是什么？为什么 k 取 60？
72. RRF 和 Convex Combination 有什么区别？
73. RRF 的分数怎么计算的？
74. RRF 能保证比单路检索好吗？
75. 如果 BM25 和 Vector 的结果完全重叠，RRF 效果怎么样？

## 十六、Chunk（5 题）

76. chunk_size=600 怎么确定的？有没有实验数据？
77. overlap=100 够吗？会不会丢失上下文？
78. 中文和英文的 chunk 策略一样吗？
79. 有没有考虑语义切分（按段落/标题）代替固定长度？
80. chunk 数量太多会影响检索性能吗？

## 十七、Retriever（5 题）

81. Retriever 和 ChromaStore 为什么分开？
82. similarity_search 的实现原理是什么？
83. search 方法返回多少条结果是合理的？
84. 怎么评估 retrieval 的质量？
85. 如果新增一种检索方式（比如图检索），架构上怎么扩展？

## 十八、Compression/Trimming（5 题）

86. 消息修剪为什么不用 token 计数而是按轮数？
87. 只保留 3 轮对话，第 4 轮的参考信息丢了怎么办？
88. 用户问"刚才说的那个事"，Agent 怎么知道指的是什么？
89. 有没有考虑用 LLM 做历史摘要？
90. 最长能支持多少轮对话不超 token 限制？

## 十九、Streaming（5 题）

91. SSE 和 WebSocket 什么区别？为什么选 SSE？
92. 流式输出时工具调用的结果怎么处理？
93. 如果用户在中途关闭了连接怎么办？
94. 流式输出的性能瓶颈在哪？
95. 怎么保证流式输出不丢数据？

## 二十、Provider（5 题）

96. Provider Registry 的设计模式叫什么？
97. 怎么增加一个新的 Provider？需要改哪些文件？
98. DeepSeek 的 API 和 OpenAI 兼容的，有什么坑吗？
99. Provider 创建 LLM 实例时 temperature 怎么设置比较合理？
100. 如果 DeepSeek API 挂了，能自动切换到备用模型吗？

## 二十一、MCP（5 题）

101. MCP 协议是什么？和普通 REST API 有什么区别？
102. MCP Server 为什么作为独立进程而不是线程？
103. MCP 的 retry_interceptor 怎么工作的？
104. MultiServerMCPClient 如何管理多个服务器连接？
105. MCP 在 Windows 上为什么连不上？是配置问题还是协议问题？

## 二十二、Tool Calling（5 题）

106. LLM 怎么决定调用哪个工具？底层机制是什么？
107. tool description 怎么写才有效？
108. 如果 LLM 调用了不存在的工具 ID 怎么办？
109. 工具返回的结果 LLM 怎么处理？
110. 多个工具调用结果冲突时怎么处理？

## 二十三、多轮对话（5 题）

111. 多轮对话里的知识库检索是每次都查吗？还是只查第一次？
112. 用户说"刚才那个问题再解释一下"，Agent 能理解吗？
113. 如果用户中途切换话题，历史消息怎么处理？
114. 多轮对话的 session 管理怎么实现的？
115. 支持多少个并发 session？

## 二十四、Token Budget（5 题）

116. 每轮对话大概消耗多少 token？
117. 知识库上下文大概多少 token？
118. 消息修剪能节省多少 token？
119. 有没有计算过单次对话的平均成本？
120. 怎么控制 token 消耗不超标？

## 二十五、异常处理（5 题）

121. Agent 调用工具超时了怎么办？
122. LLM 返回格式不对（不是预期的 JSON）怎么办？
123. 向量数据库连接失败了怎么降级？
124. 多步操作中某一步失败，是重试还是跳过？
125. 系统稳定性的指标是什么？

## 二十六、性能优化（5 题）

126. RAG 检索平均延迟 192ms，瓶颈在哪里？
127. LLM 响应 8.1s 太慢了，怎么优化？
128. 有没有做缓存？哪些数据可以缓存？
129. 并发请求多了会有什么问题？
130. 怎么评估当前系统的性能上限？

## 二十七、工程化（5 题）

131. 项目有没有测试？覆盖率多少？
132. 配置管理怎么做的？不同环境怎么切换配置？
133. 日志打了哪些信息？线上怎么排查问题？
134. 项目的目录结构怎么设计的？有什么考虑？
135. 依赖管理用的什么工具？怎么保证构建可复现？

## 二十八、为什么不用 XXX（5 题）

136. 为什么不用 Elasticsearch 做日志检索？
137. 为什么不用 Redis 做记忆存储？
138. 为什么不用 PostgreSQL pgvector？
139. 为什么不用 Weaviate？
140. 为什么不用 Milvus？

## 二十九、如何继续优化（5 题）

141. 如果给一个月时间继续优化，你最优先做哪三件事？
142. 当前的 RAG 准确率 85%，怎么提升到 95%？
143. 怎么降低 LLM 的 8 秒平均延迟？
144. 怎么验证系统的可靠性？
145. 怎么给这个系统加监控？

## 三十、重构设计（5 题）

146. 如果重写这个项目，你会做哪些不同的设计决策？
147. 架构上最大的改进空间在哪里？
148. 如果要支持多租户（多个实验室共用），架构怎么改？
149. 如果要接入真实的生产环境，需要做哪些准备工作？
150. 如果要商业化，你觉得最大的挑战是什么？

---

# 第五部分：标准回答（精选 30 道核心题）

### Q1: 为什么要做 Hybrid Search，而不是纯向量检索？

【面试官为什么问】
考察对检索技术的理解深度，是否理解不同检索方式的适用场景。

【回答思路】
从日志数据和自然语言的区别切入，说明运维场景的特点决定需要关键词匹配和语义匹配结合。

【标准回答】
两方面的原因。第一是数据特点，运维日志里有大量的错误码、异常名（OOM、SIGKILL、NullPointerException），这些是精确关键词，Embedding 虽然能把它们和同类错误聚在一起，但精度上不如 BM25 的精确命中。比如搜 "OOM"，BM25 能精确匹配到含 OOM 这个串的文档，Vector 可能会把 OutOfMemoryError、内存不足、GC overhead 这些语义相近但不同的东西都拉进来。

第二是我实际测试验证过的。在 100 条测试集上，纯向量检索的 HitRate@5 是 87%，加上 BM25 + RRF 融合后提升到 91%。这 4% 的提升主要来自那些包含精确关键词的查询，比如 "SIGKILL"、"Too many connections"。

【如果追问】
追问：BM25 和 Vector 结果冲突时以谁为准？
回答：不用"以谁为准"，RRF 会按排名融合。假设 BM25 把文档 A 排第 1、B 排第 10，Vector 把 B 排第 2、A 排第 20，RRF 算完两个文档的得分后 B 可能排到 A 前面。融合的逻辑是"两边都排名靠前的肯定重要"，而不是"BM25 或 Vector 谁说了算"。

### Q2: 为什么用 Chroma 不是 Milvus？

【面试官为什么问】
考察向量数据库选型的决策能力，是否理解不同方案的技术特性。

【回答思路】
从部署复杂度、数据规模、开发效率三个角度分析。

【标准回答】
核心原因是实验室场景不需要 Milvus 那么重的方案。Chroma 是嵌入式数据库，数据存在本地文件，pip install 就能用，不需要 Docker、不需要 etcd、不需要独立的服务进程。

Milvus 的优势在分布式的超大规模场景——百亿级向量、多副本、滚动升级这些。但我的知识库才 90 个分片，用 Milvus 完全是杀鸡用牛刀。Chroma 单机能支持百万级向量，对实验室场景绰绰有余。

第三是开发效率。Chroma 有 LangChain 的原生集成，接口和 LangChain 的 VectorStore 完全兼容，代码量减少很多。Milvus 的 pymilvus 客户端配置比较复杂，连接管理、集合创建都需要额外代码。

【如果追问】
追问：Chroma 数据存在本地文件，多个进程能同时访问吗？
回答：不能。Chroma 的持久化是通过 SQLite 实现的，单写多读都不太支持。如果多人同时访问，要么用 Chroma 的 HTTP Server 模式，要么升级到 Milvus 或 Qdrant。但 CLI 场景每次只有一个用户，单进程访问 Chroma 足够了。

### Q3: 为什么用 LangGraph 而不是自己写状态机？

【面试官为什么问】
考察框架选型能力，是否理解 LangGraph 解决的问题。

【标准回答】
自己写状态机能做，但需要处理很多边缘情况。比如 ReAct 循环里，LLM 返回 tool_calls 后要自动执行工具，执行完结果要拼回消息列表，然后再发给 LLM，同时还要处理流式输出、错误重试、循环终止条件。这些 LangGraph 的 create_react_agent 和 ToolNode 都封装好了。

Plan-Execute-Replan 的自定义状态机也是，StateGraph 帮我处理了节点间的状态传递、条件边的路由、checkpointer 的自动保存。自己写的话这些都要手动实现，而且测试覆盖要花很多时间。

我自己的原则是：框架能解决的问题不要自己造轮子，除非框架本身是瓶颈。LangGraph 目前对我来说不是瓶颈。

【如果追问】
追问：LangGraph 有什么缺点？
回答：有两个。一是调试困难，状态图的执行是黑盒，一旦出现意料之外的行为很难追踪。二是版本不稳定，langgraph 从 0.1 到 1.0 的 API 变化很大，升级可能要改代码。

### Q4: 为什么 SSE 不是 WebSocket？

【标准回答】
SSE 和 WebSocket 都能实现流式输出，但场景不同。我的需求是服务器单向推送文本到客户端——LLM 生成的字逐个流到前端。这是典型的 SSE 场景，SSE 原生支持文本流、自动重连、事件类型区分。

WebSocket 是全双工协议，适合双向实时通信（聊天、游戏）。对项目来说 WebSocket 太重了，需要额外处理心跳、连接状态管理、消息帧解析。SSE 就简单得多，Response 返回 media type 为 text/event-stream，框架自动处理。

### Q5: MemorySaver 存在内存里，重启就丢了怎么办？

【标准回答】
这是设计上权衡的结果。MemorySaver 是 LangGraph 的默认实现，数据存在进程内存里，CLI 退出就清空。对于实验室 CLI 场景这是合理的——用户跑一次 CLI 解决一个问题，会话和 CLI 进程的生命周期一致，不需要长期保存。

如果要做持久化，LangGraph 提供了 PostgresSaver 和 RedisSaver 接口，替换 checkpointer 即可，不需要改业务代码。这是抽象设计的好处——实现可以切换，接口不变。

### Q6: 怎么防止 LLM 忽略知识库内容自己编？

【标准回答】
三个层面。第一是 Prompt 设计，System Message 里明确写"基于以下知识库内容回答问题"，知识库上下文放在工具描述之前，引导 LLM 优先使用。第二是 RAG 结果的质量保证，Hybrid Search 保证检索到的文档和问题相关，LLM 没理由忽略。第三是工具调用机制，如果 LLM 不确定答案，它可以调 retrieve_knowledge 工具查知识库，而不是自己编。

但这三个都不是万能的。LLM 有固有幻觉倾向，最好的防御是让用户能验证——CLI 输出中标注信息来源（如`【参考资料 1】来源: cpu-usage.md`），用户可以判断回答是否可靠。

### Q7: Agent 工具调用失败怎么处理？

【标准回答】
分两层。第一层是 MCP 工具的重试拦截器，当调用失败时默认重试 3 次，指数退避（1s、2s、4s），如果 3 次都失败返回错误信息而不是抛异常。

第二层是 Agent 层的容错。ToolNode 执行工具后，不管成功还是失败，结果都会以 ToolMessage 形式返回给 LLM。LLM 看到工具调用结果后可以决定下一步怎么走——如果工具失败了，LLM 可以换一个工具，或直接告诉用户执行失败原因。

这个设计的核心原则是"不让一个工具的失败拖垮整个 Agent 流程"。

### Q8: 怎么评估 RAG 检索质量？

【标准回答】
我建了 100 条运维测试集，每条包含 query、期望的文档、期望的回答关键词。评估指标用 HitRate@K，即正确答案是否出现在前 K 个检索结果中。这是信息检索领域最常用的评估方法。

具体操作是遍历 100 条查询，对每个 query 调 similarity_search 取 TopK，检查返回结果中是否包含期望的文档。计算命中率。同时记录了平均检索延迟。

实测结果：HitRate@3 85%，HitRate@5 87%，平均延迟 192ms。这个数据说明检索质量不错，大多数情况下正确的文档在前 3 个结果里就能找到。

---

# 第六部分：深挖问题

## 为什么用 Chroma 不是 PostgreSQL pgvector？

pgvector 需要在 PostgreSQL 上加扩展，虽然性能不差但部署复杂。实验室场景没有已有的 PostgreSQL，为了向量检索再搭一个数据库太浪费。Chroma 零配置就能用。

如果之后数据量到百万级或需要和其他业务数据做联合查询，pgvector 是更合理的方案。但当前阶段 Chroma 足够了。

## 为什么不用 Elasticsearch？

Elasticsearch 能做全文检索（类似 BM25）也能做向量检索，功能上确实可以替代我的 Chroma + BM25。但 ES 太重了——需要 Java 运行时、集群部署、索引管理。实验室场景追求快速开发和低维护成本，不需要 ES 的企业级能力。

而且我的 Hybrid Search 架构（BM25 + Vector + RRF）换成 ES 也不是不行，只是没有必要。

## 为什么不用 Agent 框架（AutoGen/CrewAI）？

AutoGen 和 CrewAI 都是多 Agent 框架，解决的是"多个 Agent 怎么协作"的问题。而我只需要一个 Agent。多 Agent 的开销——角色定义、任务分配、消息路由、竞争条件——对我来说完全没有必要。

LangGraph 是更好的选择，它专注"一个 Agent 内部的工作流"，这是真正需要解决的问题。

## 为什么不用向量数据库的 Hybrid Search 内置功能？

大部分向量数据库（Weaviate、Qdrant、Milvus）都支持内置的 Hybrid Search。但因为选了 Chroma（理由见上），Chroma 本身不支持 Hybrid Search，所以自己实现了 BM25 + RRF。

这也说明一个取舍：选了简单的向量数据库（Chroma），就要自己实现额外功能（Hybrid Search）。如果一开始就选 Weaviate，就省了这部分工作但多了运维成本。

---

# 第七部分：压力面模拟

面试官：为什么要做 Agent？用脚本不行吗？

答：脚本能解决固定流程的问题。但运维场景的变化太多——同样是 OOM，可能是内存泄漏、流量突增、JVM 参数不合理，每种情况的排查步骤和解决方案都不一样。脚本没法智能判断走哪条路。

面试官：为什么不是 if-else？

答：if-else 的判断条件需要人提前写好，但问题空间的组合是指数级的——不同的错误类型、不同的系统状态、不同的历史记录，if-else 写不完的。LLM 的优势是面对 new combination 的时候能推理出合理的判断。

面试官：那你怎么保证 LLM 的推理是正确的？

答：不能 100% 保证。所以加了三层保障：第一层是 RAG，让回答基于知识库而不是幻觉；第二层是工具调用，LLM 要做的是调用工具获取真实数据，而不是编造数据；第三层是信息来源标注，用户能判断可靠性。

面试官：这三层保障能 100% 解决幻觉吗？

答：不能。但我也没见过什么方案能 100% 解决幻觉。我的目标是降低幻觉到可接受的程度——85% 的 RAG 准确率 + 93% 的关键词覆盖率 + 来源标注，在实验室场景下够用了。

面试官：93% 的关键词覆盖率是采样 20 条算的，采样方法是不是有问题？

答：确实有问题。20 条采样全部来自前几个类别（memory、cpu），不能代表整体的 100 条。更准确的评估应该随机采样或分层采样。不过关键词覆盖率本身是个粗糙的指标，我主要用它来快速发现 LLM 是否偏离知识库。精确的 answer quality 评估需要人工评测。

面试官：怎么不做人工评测？

答：人力成本。100 条测试全部人工评估需要 2-3 小时。Keyword Coverage 虽然粗糙，但自动化运行只需要几分钟。在迭代阶段先用自动化指标跑，到最终评估阶段再做人工采样。

面试官：如果给你一个月，你最想优化什么？

答：第一，扩大测试集到 500 条并做人工标注，拿到更可靠的质量数据。第二，降低 LLM 延迟，考虑用 streaming 加 partial response 的方案，让用户在 LLM 完全生成完之前就能看到部分结果。第三，在生产环境部署一套，接入真实的 journalctl 日志，跑一个月的稳定性验证。

---

# 第八部分：风险问题

## 项目是不是自己写的？

是。从设计到编码到文档全部独立完成。代码仓库的 commit 记录可以证明——78 个文件、5749 行代码，每次 commit 都是渐变式构建。代码里有我的编码风格，比如注释少、命名清晰、模块拆分合理。

如果面试官怀疑，我可以现场讲解任意模块的代码细节。

## 有没有参考开源项目？

参考了 LangChain 官方教程中的 ReAct Agent 实现和 Plan-Execute-Replan 教程。代码没有直接复制，是根据我的项目需求重新实现的。比如 Plan-Execute-Replan 的约束条件（最多 8 步、5 步后禁止 replan）是根据运维场景自己加的。

## 有没有真正上线？

目前在 Windows 开发环境运行，模拟日志模式下全流程验证通过。部署到 Linux 服务器只需要把代码拉到目标机器、安装依赖、配置环境变量即可运行，MCP 工具会自动使用真实的 journalctl 命令。

## 性能数据有没有压测？

RAG 检索做了量化评估（100 条测试集），LLM 回答做了采样评估（20 条）。没有做并发压测，因为场景是 CLI 单用户使用，不涉及高并发。如果要做压测，可以用 locust 模拟多用户同时查询，但当前阶段这不是重点。

---

# 第九部分：总结

## 做得好的地方

1. **架构清晰**：四层分层、模块解耦、职责单一，经得起推敲
2. **技术选型合理**：Chroma、LangGraph、MCP 的选择都有明确的理由
3. **评估数据量化**：不是"效果还不错"而是"HitRate@3=85%"
4. **Hybrid Search**：纯向量 + BM25 + RRF 的组合在运维场景确实有效
5. **主动监控**：Log Watcher + Rule Engine + AlertManager 的链路完整
6. **项目管理**：从设计到开发到测试到评估，完整的软件工程链路

## 需要继续完善的地方

1. **测试覆盖**：目前几乎没有正式的单测
2. **人工评估**：关键词覆盖率是自动化指标，需要人工评测补充
3. **生产部署**：没有真正的生产环境验证
4. **MCP Server 兼容性**：Windows 上无法正常启动，Linux 上未验证
5. **缓存**：没有对重复查询做缓存，浪费 API 调用
6. **并发支持**：目前只有单用户，多用户同时使用会出问题

## 最容易被问的地方

1. **Chroma vs Milvus 选型**：高频问题，要能流畅回答
2. **LangGraph vs 自己写状态机**：考察框架理解深度
3. **Hybrid Search 的设计**：为什么这样做、RRF 原理、BM25 和 Vector 的互补
4. **RAG 评估数据**：能说清 85%、93% 分别怎么算的
5. **MCP 在 Windows 上为什么不行**：说实话，实话是最好的策略

## 最值得重点准备的地方

1. **项目架构图**：能画出四层架构，说清每层职责和数据流
2. **检索流程**：把 Hybrid Search 的 BM25→Vector→RRF→Reranker 流程讲透
3. **Agent 流程**：区分 ReAct（对话）和 Plan-Execute-Replan（诊断）两种模式
4. **选型理由**：每个技术选型都能从三个角度回答（为什么选这个、不选那个、优缺点）
5. **评估方法**：能说清怎么建测试集、怎么算指标、指标的局限性
