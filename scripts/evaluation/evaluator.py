"""
Linux AIOps Agent - 自动化评估框架

评估指标:
  - RAG Hit Rate@K (K=1,3,5,10)
  - Answer Correctness (关键词覆盖率)
  - Average Latency (检索 + LLM)
  - Hybrid Search vs Pure Vector 对比

用法:
    cd linux-aiops-agent
    python scripts/evaluation/evaluator.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.retrieval.chroma_store import ChromaStore
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.splitter import DocumentSplitter
from app.retrieval.reranker import Reranker
from app.providers.registry import ProviderRegistry
from app.services.knowledge_service import knowledge_service
from langchain_core.messages import HumanMessage, SystemMessage


def load_dataset(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_rag_hit_rate(dataset: list, top_k_list: list = [1, 3, 5, 10]) -> dict:
    """RAG 检索准确率 (Hit Rate@K)"""
    results = {}
    for k in top_k_list:
        correct = 0
        latencies = []
        for item in dataset:
            q = item["question"]
            expected = item["expected_doc"]
            t0 = time.time()
            docs = knowledge_service.retriever.store.similarity_search(q, k=k)
            latencies.append((time.time() - t0) * 1000)
            retrieved = {d.metadata.get("_file_name", "").replace(".md", "") for d in docs}
            if expected in retrieved:
                correct += 1
        results[f"HitRate@{k}"] = {
            "accuracy": round(correct / len(dataset) * 100, 1),
            "correct": correct,
            "total": len(dataset),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
        }
    return results


def evaluate_hybrid_vs_vector(dataset: list, top_k: int = 5) -> dict:
    """对比 Hybrid Search 和 Pure Vector Search"""
    store = knowledge_service.retriever.store
    hybrid = knowledge_service.retriever

    vector_correct = 0
    hybrid_correct = 0
    vector_time = 0
    hybrid_time = 0

    for item in dataset:
        q = item["question"]
        expected = item["expected_doc"]

        t0 = time.time()
        v_docs = store.similarity_search(q, k=top_k)
        vector_time += (time.time() - t0) * 1000
        v_retrieved = {d.metadata.get("_file_name", "").replace(".md", "") for d in v_docs}
        if expected in v_retrieved:
            vector_correct += 1

        t0 = time.time()
        h_docs = hybrid.search(q, top_k=top_k)
        hybrid_time += (time.time() - t0) * 1000
        h_retrieved = {d.metadata.get("_file_name", "").replace(".md", "") for d in h_docs}
        if expected in h_retrieved:
            hybrid_correct += 1

    n = len(dataset)
    return {
        "PureVector": {
            "accuracy": round(vector_correct / n * 100, 1),
            "avg_latency_ms": round(vector_time / n, 1),
        },
        "HybridSearch": {
            "accuracy": round(hybrid_correct / n * 100, 1),
            "avg_latency_ms": round(hybrid_time / n, 1),
        },
        "improvement": round((hybrid_correct - vector_correct) / n * 100, 1),
    }


def evaluate_answer_correctness(dataset: list, sample_size: int = 20) -> dict:
    """LLM 回答质量评估 (取前 sample_size 条)"""
    llm = ProviderRegistry.get_llm(temperature=0, streaming=False)

    results = []
    total_keywords = 0
    matched_keywords = 0

    for item in dataset[:sample_size]:
        q = item["question"]
        keywords = item.get("expected_keywords", [])
        if not keywords:
            continue

        context = knowledge_service.search(q)
        t0 = time.time()
        resp = llm.invoke([
            SystemMessage(content=f"基于以下知识库内容回答问题:\n{context}\n请用中文回答。"),
            HumanMessage(content=q),
        ])
        latency = (time.time() - t0) * 1000
        answer = resp.content if hasattr(resp, "content") else str(resp)

        matched = sum(1 for kw in keywords if kw.lower() in answer.lower())
        total_keywords += len(keywords)
        matched_keywords += matched

        results.append({
            "id": item["id"],
            "question": q,
            "keyword_coverage": f"{matched}/{len(keywords)}",
            "latency_ms": round(latency, 0),
        })

    coverage = round(matched_keywords / total_keywords * 100, 1) if total_keywords else 0
    avg_latency = round(sum(r["latency_ms"] for r in results) / len(results), 0) if results else 0

    return {
        "keyword_coverage": f"{coverage}%",
        "avg_llm_latency_ms": avg_latency,
        "sample_size": len(results),
        "details": results,
    }


def main():
    dataset_path = Path(__file__).parent / "test_dataset.json"
    dataset = load_dataset(str(dataset_path))
    print(f"\n{'='*60}")
    print(f"  Linux AIOps Agent - 自动化评估")
    print(f"  Test Dataset: {len(dataset)} queries")
    print(f"{'='*60}\n")

    # 1. RAG Hit Rate
    print("[1/3] RAG Hit Rate Evaluation")
    print("-" * 40)
    hit_results = evaluate_rag_hit_rate(dataset)
    for k, v in hit_results.items():
        print(f"  {k:>10}: {v['accuracy']:>5.1f}%  ({v['correct']}/{v['total']})  avg: {v['avg_latency_ms']}ms")
    print()

    # 2. Hybrid vs Vector
    print("[2/3] Hybrid Search vs Pure Vector")
    print("-" * 40)
    cmp = evaluate_hybrid_vs_vector(dataset)
    for method, v in cmp.items():
        if method != "improvement":
            print(f"  {method:>15}: {v['accuracy']:>5.1f}%  avg: {v['avg_latency_ms']}ms")
    print(f"  {'Improvement':>15}: {cmp['improvement']:>+.1f}%")
    print()

    # 3. Answer Correctness
    print("[3/3] LLM Answer Quality (sample: 20)")
    print("-" * 40)
    ans = evaluate_answer_correctness(dataset, sample_size=min(20, len(dataset)))
    print(f"  Keyword Coverage: {ans['keyword_coverage']}")
    print(f"  Avg LLM Latency: {ans['avg_llm_latency_ms']:.0f}ms")
    for d in ans["details"][:5]:
        print(f"    {d['id']}: {d['keyword_coverage']} keywords  {d['latency_ms']:.0f}ms")
    print(f"    ... and {len(ans['details'])-5} more")
    print()

    # Summary
    print(f"{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    best_k = max(hit_results, key=lambda k: hit_results[k]["accuracy"])
    print(f"  RAG Best:         {hit_results[best_k]['accuracy']}% {best_k}")
    print(f"  Hybrid Improvement: {cmp['improvement']:+.1f}% vs Pure Vector")
    print(f"  Keyword Coverage:  {ans['keyword_coverage']}")
    print(f"  Avg RAG Latency:   {hit_results['HitRate@5']['avg_latency_ms']}ms")
    print(f"  Avg LLM Latency:   {ans['avg_llm_latency_ms']:.0f}ms")

    # Save report
    report = {
        "dataset_size": len(dataset),
        "rag_hit_rate": hit_results,
        "hybrid_vs_vector": cmp,
        "answer_quality": ans,
    }
    report_path = Path(__file__).parent / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  Report saved: {report_path}")
    print()


if __name__ == "__main__":
    main()
