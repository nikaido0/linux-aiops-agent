from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from loguru import logger
from app.retrieval.chroma_store import ChromaStore
from app.retrieval.splitter import DocumentSplitter
from app.retrieval.reranker import Reranker
from app.retrieval.hybrid_retriever import HybridRetriever


class KnowledgeService:
    """知识库服务 — 统一入口

    职责:
    - 文档摄入（单个文件/整个目录）
    - 知识检索（query → 格式化上下文）
    - 屏蔽底层检索细节（Chroma、Reranker、Splitter 等）

    调用方只需:
        knowledge_service.search("CPU 使用率高怎么办")
        knowledge_service.ingest_file("./knowledge/linux/cpu-usage.md")
    """

    def __init__(self):
        store = ChromaStore(collection_name="linux_ops")
        splitter = DocumentSplitter()
        reranker = Reranker()
        self.retriever = HybridRetriever(store=store, splitter=splitter, reranker=reranker)
        logger.info("KnowledgeService 初始化完成")

    def ingest_file(self, file_path: str) -> int:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        content = path.read_text(encoding="utf-8")
        doc = Document(
            page_content=content,
            metadata={
                "_source": path.as_posix(),
                "_file_name": path.name,
                "_extension": path.suffix,
            },
        )
        ids = self.retriever.ingest([doc])
        logger.info(f"文件 {path.name} 已摄入, {len(ids)} 个分片")
        return len(ids)

    def ingest_directory(self, directory: str, pattern: str = "*.md") -> int:
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        total = 0
        for file_path in path.glob(pattern):
            try:
                count = self.ingest_file(str(file_path))
                total += count
                logger.info(f"✓ {file_path.name} -> {count} 分片")
            except Exception as e:
                logger.error(f"✗ {file_path.name}: {e}")
        return total

    def search(self, query: str, top_k: Optional[int] = None) -> str:
        docs = self.retriever.search(query, top_k=top_k)
        if not docs:
            return "没有找到相关信息。"

        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("_file_name", "未知来源")
            parts.append(f"【参考资料 {i}】\n来源: {source}\n内容:\n{doc.page_content}\n")
        return "\n".join(parts)

    def count_documents(self) -> int:
        return self.retriever.store.count()


knowledge_service = KnowledgeService()
