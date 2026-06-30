"""
RAG 参数优化测试 — 基于真实 Chroma + DashScope Embedding

测试不同 chunk_size × top_k 组合的检索准确率。
由于 chunk_size 变化需要重新注入文档（会调用 Embedding API），
先测试 top_k 对检索效果的影响，再快速验证不同 chunk_size 的差异。

用法:
    conda activate linux-aiops
    cd linux-aiops-agent && python scripts/rag_evaluation.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import config
from app.retrieval.chroma_store import ChromaStore
from app.retrieval.splitter import DocumentSplitter
from app.retrieval.embeddings import DashScopeEmbeddings
from app.retrieval.reranker import Reranker
from langchain_core.documents import Document
from loguru import logger

###############################################################################
# 测试查询: (query, 期望的文档文件名)
###############################################################################

TEST_QUERIES = [
    ("CPU 使用率过高怎么排查", "cpu-usage"),
    ("服务器 CPU 跑到 100% 了怎么办", "cpu-usage"),
    ("CPU 告警处理流程", "cpu-usage"),
    ("top 命令看到 CPU 占用高如何定位", "cpu-usage"),
    ("服务器负载过高如何排查", "cpu-usage"),
    ("内存使用率过高如何处理", "memory-usage"),
    ("OOM Killer 杀死了进程怎么办", "memory-usage"),
    ("JVM 内存溢出如何排查", "memory-usage"),
    ("free -h 显示内存不足", "memory-usage"),
    ("磁盘空间不足怎么清理", "disk-usage"),
    ("磁盘使用率超过 90% 如何解决", "disk-usage"),
    ("日志文件太大怎么处理", "disk-usage"),
    ("Docker 镜像占用磁盘空间怎么清理", "disk-usage"),
    ("服务起不来了怎么办", "service-unavailable"),
    ("systemctl status 显示服务 failed", "service-unavailable"),
    ("端口被占用如何排查", "service-unavailable"),
    ("健康检查失败怎么办", "service-unavailable"),
    ("网络不通怎么排查", "network-troubleshooting"),
    ("DNS 解析失败怎么办", "network-troubleshooting"),
    ("iptables 挡住了端口", "network-troubleshooting"),
    ("连接数过多怎么处理", "network-troubleshooting"),
    ("接口响应太慢如何优化", "slow-response"),
    ("数据库慢查询怎么排查", "slow-response"),
    ("缓存穿透怎么解决", "slow-response"),
]

###############################################################################
# 知识库文档路径
###############################################################################

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge" / "linux"
DOC_FILES = sorted(KNOWLEDGE_DIR.glob("*.md"))


def load_docs() -> dict:
    """加载知识库所有文档"""
    docs = {}
    for f in DOC_FILES:
        docs[f.stem] = f.read_text(encoding="utf-8")
    return docs


def clear_chroma():
    """清空 Chroma 集合（重新注入前调用）"""
    import shutil
    chroma_dir = Path("./chroma_data")
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        logger.info("Chroma 数据已清空")


_test_counter = 0

def inject_with_chunk_size(chunk_size: int) -> ChromaStore:
    """以指定 chunk_size 重新注入文档，使用独立 collection 名避免冲突"""
    global _test_counter
    _test_counter += 1
    collection_name = f"eval_{_test_counter}_cs_{chunk_size}"
    chroma_dir = Path(f"./chroma_data_{collection_name}")

    store = ChromaStore(collection_name=collection_name, persist_directory=str(chroma_dir))
    splitter = DocumentSplitter(chunk_size=chunk_size, chunk_overlap=max(20, chunk_size // 6))
    embeddings = DashScopeEmbeddings()

    for doc_file in DOC_FILES:
        content = doc_file.read_text(encoding="utf-8")
        raw_doc = Document(
            page_content=content,
            metadata={"_source": doc_file.as_posix(), "_file_name": doc_file.name, "_extension": ".md"},
        )
        chunks = splitter.split_documents([raw_doc])
        store.add_documents(chunks)
        logger.info(f"  {doc_file.name} -> {len(chunks)} 分片")

    logger.info(f"注入完成, chunk_size={chunk_size}, 共 {store.count()} 分片")
    return store


def evaluate_top_k(store: ChromaStore, top_k: int) -> float:
    """评估给定 top_k 的检索准确率 (Hit Rate)"""
    correct = 0
    for query, expected_doc in TEST_QUERIES:
        results = store.similarity_search(query, k=top_k)
        retrieved_sources = set()
        for doc in results:
            source = doc.metadata.get("_file_name", "")
            retrieved_sources.add(source.replace(".md", ""))

        if expected_doc in retrieved_sources:
            correct += 1

    return round(correct / len(TEST_QUERIES) * 100, 1)


def main():
    print("=" * 60)
    print("  RAG 参数优化测试 — 真实 Embedding + Chroma")
    print("=" * 60)
    print(f"\n📚 文档: {len(DOC_FILES)} 篇")
    print(f"📝 测试查询: {len(TEST_QUERIES)} 条")
    print()

    # === 阶段 1: 测试 chunk_size=600 时不同 top_k 的表现 ===
    print("─" * 50)
    print("阶段 1: chunk_size=600, 测试 top_k 影响")
    print("─" * 50)

    store = inject_with_chunk_size(600)

    print(f"\n{'top_k':>6} | {'准确率':>8} | 分析")
    print("-" * 50)
    results_topk = {}
    for k in [1, 2, 3, 5, 7, 10]:
        acc = evaluate_top_k(store, k)
        results_topk[k] = acc
        if acc >= 85:
            analysis = "🟢 推荐范围"
        elif acc >= 70:
            analysis = "🟡 可接受"
        else:
            analysis = "🔴 偏低"
        print(f"{k:>6} | {acc:>7.1f}% | {analysis}")

    # === 阶段 2: 测试不同 chunk_size 的差异（只测 top_k=3 和 top_k=5）===
    print(f"\n\n{'─' * 50}")
    print("阶段 2: 测试不同 chunk_size(仅耗时测试 top_k=3)")
    print("─" * 50)

    chunk_sizes = [400, 600, 800, 1000]
    results_chunk = {}
    for cs in chunk_sizes:
        store_cs = inject_with_chunk_size(cs)
        acc = evaluate_top_k(store_cs, top_k=3)
        results_chunk[cs] = acc
        if acc >= 85:
            analysis = "🟢 推荐"
        elif acc >= 70:
            analysis = "🟡 可接受"
        else:
            analysis = "🔴 偏低"
        print(f"{cs:>6} | {acc:>7.1f}% | {analysis}")

    # === 汇总 ===
    print(f"\n\n{'=' * 60}")
    print("  测试结论")
    print("=" * 60)

    # 找最优
    best_topk_k = max(results_topk, key=results_topk.get)
    best_cs = max(results_chunk, key=results_chunk.get)

    print(f"\n🏆 最优 top_k: {best_topk_k} (准确率 {results_topk[best_topk_k]}%)")
    print(f"🏆 最优 chunk_size: {best_cs} (准确率 {results_chunk[best_cs]}%)")
    print(f"\n📊 推荐配置: chunk_size={best_cs}, top_k={best_topk_k}")

    # 保存结果
    output = {
        "method": "真实 DashScope Embedding + Chroma",
        "test_queries": len(TEST_QUERIES),
        "documents": len(DOC_FILES),
        "results_by_topk": results_topk,
        "results_by_chunk_size": results_chunk,
        "recommended": {"chunk_size": best_cs, "top_k": best_topk_k},
    }
    out_path = PROJECT_ROOT / "scripts" / "rag_evaluation_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n💾 结果已保存: {out_path}")


if __name__ == "__main__":
    main()
