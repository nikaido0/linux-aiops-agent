"""知识库文档摄入脚本

将 knowledge/ 目录下的 Markdown 文档注入 Chroma 向量库。

用法:
    cd linux-aiops-agent
    python scripts/ingest_knowledge.py
"""

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.knowledge_service import knowledge_service
from loguru import logger


def main():
    knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"

    logger.info("=" * 50)
    logger.info("开始注入知识库文档...")
    logger.info("=" * 50)

    for category_dir in sorted(knowledge_dir.iterdir()):
        if not category_dir.is_dir():
            continue

        md_files = list(category_dir.glob("*.md"))
        if not md_files:
            continue

        logger.info(f"\n📂 分类: {category_dir.name}")
        for md_file in md_files:
            try:
                chunk_count = knowledge_service.ingest_file(str(md_file))
                logger.info(f"  ✓ {md_file.name} → {chunk_count} 个分片")
            except Exception as e:
                logger.error(f"  ✗ {md_file.name}: {e}")

    doc_count = knowledge_service.count_documents()
    logger.info(f"\n{'=' * 50}")
    logger.info(f"注入完成! 共 {doc_count} 个文档分片")
    logger.info(f"{'=' * 50}")


if __name__ == "__main__":
    main()
