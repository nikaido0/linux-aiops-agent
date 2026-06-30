"""
快速 RAG 检索测试 — 验证知识库检索功能是否正常

用法:
    conda activate linux-aiops
    cd linux-aiops-agent && python scripts/rag_search_test.py
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.knowledge_service import knowledge_service


def main():
    test_questions = [
        "CPU 使用率过高怎么排查",
        "内存不够用了怎么办",
        "磁盘空间满了如何清理",
        "服务起不来怎么处理",
        "网络不通怎么排查",
        "接口响应慢如何优化",
    ]

    print("=" * 60)
    print("  RAG 知识库检索测试")
    print("=" * 60)

    for q in test_questions:
        print(f"\n📝 查询: {q}")
        print("-" * 40)
        result = knowledge_service.search(q)
        # 只显示前 200 字符
        preview = result[:200] if result else "(空)"
        print(f"📎 结果: {preview}...")
        print()

    doc_count = knowledge_service.count_documents()
    print(f"\n📊 Chroma 文档总数: {doc_count} 分片")


if __name__ == "__main__":
    main()
