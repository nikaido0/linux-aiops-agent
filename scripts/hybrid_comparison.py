"""
Hybrid Search vs Pure Vector Search 对比测试

测试两组查询:
  1. 自然语言查询（运维场景问法）
  2. 日志关键词查询（OOM, SIGKILL 等精确匹配）

验证 Hybrid Search (BM25 + Vector + RRF + Reranker) 相比 Pure Vector Search 的优势。
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.knowledge_service import knowledge_service
from app.retrieval.chroma_store import ChromaStore

###############################################################################
# 测试查询
###############################################################################

NL_QUERIES = [
    ("CPU 使用率过高怎么排查", "cpu-usage"),
    ("内存不够用了怎么办", "memory-usage"),
    ("磁盘空间满了如何清理", "disk-usage"),
    ("服务起不来怎么处理", "service-unavailable"),
    ("网络不通怎么排查", "network-troubleshooting"),
    ("接口响应慢如何优化", "slow-response"),
]

# 日志风格查询 - 这是 Hybrid Search 的优势场景
LOG_QUERIES = [
    ("OOM killer 杀死了进程", "memory-usage"),
    ("OutOfMemoryError Java heap space", "memory-usage"),
    ("SIGKILL signal 9", "memory-usage"),
    ("NullPointerException 空指针异常", "slow-response"),
    ("Connection refused connect", "service-unavailable"),
    ("Too many connections 数据库连接池满", "slow-response"),
    ("No space left on device", "disk-usage"),
    ("FileNotFoundException 日志文件", "disk-usage"),
    ("Permission denied 权限不足", "disk-usage"),
    ("Connection timeout 超时", "network-troubleshooting"),
    ("DNS resolution failed 域名解析失败", "network-troubleshooting"),
    ("iptables DROP 包被丢弃", "network-troubleshooting"),
    ("systemctl start failed 服务启动失败", "service-unavailable"),
    ("docker system prune 清理磁盘", "disk-usage"),
    ("journalctl 日志查看", "service-unavailable"),
]


def evaluate_pure_vector(store: ChromaStore, queries: list, top_k: int = 5) -> float:
    """纯 Vector Search 评估"""
    correct = 0
    for query, expected in queries:
        results = store.similarity_search(query, k=top_k)
        retrieved = set()
        for d in results:
            fn = d.metadata.get("_file_name", "").replace(".md", "")
            retrieved.add(fn)
        if expected in retrieved:
            correct += 1
    return round(correct / len(queries) * 100, 1)


def evaluate_hybrid(queries: list, top_k: int = 5) -> float:
    """Hybrid Search 评估"""
    correct = 0
    for query, expected in queries:
        results = knowledge_service.retriever.search(query, top_k=top_k)
        retrieved = set()
        for d in results:
            fn = d.metadata.get("_file_name", "").replace(".md", "")
            retrieved.add(fn)
        if expected in retrieved:
            correct += 1
    return round(correct / len(queries) * 100, 1)


def show_detail(store: ChromaStore, label: str, queries: list, top_k: int = 5):
    """显示每条查询的命中情况"""
    correct = 0
    vector_method = "vector_only" in label.lower()

    for query, expected in queries:
        if vector_method:
            results = store.similarity_search(query, k=top_k)
        else:
            results = knowledge_service.retriever.search(query, top_k=top_k)

        retrieved = set()
        for d in results:
            fn = d.metadata.get("_file_name", "").replace(".md", "")
            retrieved.add(fn)

        hit = expected in retrieved
        if hit:
            correct += 1
        icon = "+" if hit else " "
        print(f"  [{icon}] {query[:50]:<50} -> {expected:<25} {'HIT' if hit else 'MISS'}")

    print(f"  {'=' * 50}")
    print(f"  准确率: {correct}/{len(queries)} = {round(correct/len(queries)*100,1)}%")


def main():
    print("=" * 65)
    print("  Hybrid Search vs Pure Vector Search 对比测试")
    print("=" * 65)

    # 获取现有的 ChromaStore 实例（用于 Pure Vector 测试）
    chroma_store = knowledge_service.retriever.store

    print(f"\n{'─' * 65}")
    print("  [测试 A] 自然语言查询 (6 条)")
    print(f"{'─' * 65}")

    print("\n  --- Pure Vector ---")
    show_detail(chroma_store, "vector_only", NL_QUERIES, top_k=5)

    print("\n  --- Hybrid (BM25+Vector+RRF) ---")
    show_detail(chroma_store, "hybrid", NL_QUERIES, top_k=5)

    print(f"\n{'─' * 65}")
    print("  [测试 B] 日志关键词查询 (15 条)")
    print(f"{'─' * 65}")

    print("\n  --- Pure Vector ---")
    show_detail(chroma_store, "vector_only", LOG_QUERIES, top_k=5)

    print("\n  --- Hybrid (BM25+Vector+RRF) ---")
    show_detail(chroma_store, "hybrid", LOG_QUERIES, top_k=5)

    # 汇总
    print(f"\n{'=' * 65}")
    print("  汇总对比")
    print(f"{'=' * 65}")

    nl_vec = evaluate_pure_vector(chroma_store, NL_QUERIES)
    nl_hyb = evaluate_hybrid(NL_QUERIES)
    log_vec = evaluate_pure_vector(chroma_store, LOG_QUERIES)
    log_hyb = evaluate_hybrid(LOG_QUERIES)

    print(f"\n  {'场景':<25} {'Pure Vector':>15} {'Hybrid':>15} {'提升':>10}")
    print(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*10}")
    print(f"  {'自然语言查询':<25} {nl_vec:>14.1f}% {nl_hyb:>14.1f}% {nl_hyb-nl_vec:>+9.1f}%")
    print(f"  {'日志关键词查询':<25} {log_vec:>14.1f}% {log_hyb:>14.1f}% {log_hyb-log_vec:>+9.1f}%")

    # 保存结果
    result = {
        "method": "Hybrid Search vs Pure Vector",
        "test_queries": {
            "natural_language": len(NL_QUERIES),
            "log_keywords": len(LOG_QUERIES),
        },
        "results": {
            "nl_pure_vector": nl_vec,
            "nl_hybrid": nl_hyb,
            "log_pure_vector": log_vec,
            "log_hybrid": log_hyb,
        },
        "improvement": {
            "nl": nl_hyb - nl_vec,
            "log": log_hyb - log_vec,
        },
    }
    out_path = PROJECT_ROOT / "scripts" / "hybrid_comparison_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {out_path}")


if __name__ == "__main__":
    main()
