"""Hybrid Retriever - BM25 + Vector Search + RRF Fusion + Reranker

设计思路:
    日志数据（OOM, SIGKILL, NullPointerException 等）本质是关键词精确匹配，
    纯 Embedding 语义搜索效果不佳。Hybrid Search 结合了两者优势：

    用户查询
      ├─→ BM25 (关键词匹配) ─→ Top30 ─┐
      │                                ├─→ RRF Fusion ─→ Reranker ─→ Top5
      └─→ Vector (语义匹配) ─→ Top30 ─┘

    BM25:  精确命中关键词，适合日志错误码/异常名
    Vector: 语义相似度匹配，适合自然语言问题
    RRF:    Reciprocal Rank Fusion，融合两种排序
    Reranker: 交叉编码器精排
"""

import re
from typing import List, Optional, Dict
from langchain_core.documents import Document
from loguru import logger
from app.config import config
from .chroma_store import ChromaStore
from .splitter import DocumentSplitter
from .reranker import Reranker


class HybridRetriever:
    """混合检索器 - BM25 + Vector + RRF + Reranker"""

    def __init__(
        self,
        store: ChromaStore,
        splitter: Optional[DocumentSplitter] = None,
        reranker: Optional[Reranker] = None,
    ):
        self.store = store
        self.splitter = splitter or DocumentSplitter()
        self.reranker = reranker or Reranker()
        self._bm25 = None
        self._chunk_texts: List[str] = []
        self._chunk_sources: List[str] = []
        # 启动时从 Chroma 重建 BM25 索引
        self._rebuild_from_store()
        logger.info("HybridRetriever 初始化完成")

    # ── Tokenizer ──────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """简单分词器: 提取字母数字 token

        日志中的关键词 (OOM, SIGKILL, NullPointerException) 都是字母数字组合，
        用 \w+ 提取即可。中文则靠 Vector Search 处理。
        """
        text = text.lower()
        tokens = re.findall(r"[a-z0-9_]+", text)
        return [t for t in tokens if len(t) > 1]

    # ── 文档摄入 ────────────────────────────────────────────

    def ingest(self, documents: List[Document]) -> List[str]:
        """摄入文档: 切分 → 存 Chroma → 建 BM25 索引"""
        chunks = self.splitter.split_documents(documents)
        self.store.add_documents(chunks)

        for chunk in chunks:
            self._chunk_texts.append(chunk.page_content)
            source = chunk.metadata.get("_file_name", "unknown")
            self._chunk_sources.append(source)

        self._rebuild_bm25()
        logger.info(f"HybridRetriever 摄入 {len(chunks)} 分片, 总计 {len(self._chunk_texts)} 分片")
        return [str(i) for i in range(len(self._chunk_texts))]

    def _rebuild_bm25(self):
        """重建 BM25 索引"""
        from rank_bm25 import BM25Okapi

        tokenized = [self._tokenize(t) for t in self._chunk_texts]
        self._bm25 = BM25Okapi(tokenized)
        logger.debug(f"BM25 索引重建完成, {len(tokenized)} 文档")

    def _rebuild_from_store(self):
        """启动时从 Chroma 加载已有文档重建 BM25 索引"""
        try:
            store = self.store._get_store()
            all_data = store.get()
            if all_data and all_data.get("documents"):
                for i, text in enumerate(all_data["documents"]):
                    self._chunk_texts.append(text)
                    meta = all_data.get("metadatas", [{}])[i] if all_data.get("metadatas") else {}
                    self._chunk_sources.append(meta.get("_file_name", "unknown"))
                if self._chunk_texts:
                    self._rebuild_bm25()
                    logger.info(f"从 Chroma 恢复 BM25 索引: {len(self._chunk_texts)} 文档")
        except Exception as e:
            logger.debug(f"从 Chroma 重建 BM25 失败 (首次运行无数据): {e}")

    # ── 检索 ────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> List[Document]:
        """混合检索: BM25 + Vector → RRF → Reranker → TopK"""
        if not self._chunk_texts or self._bm25 is None:
            logger.info("BM25 索引为空，仅使用 Vector Search")
            return self.store.similarity_search(query, k=top_k)

        # 1. BM25 召回 Top30
        query_tokens = self._tokenize(query)
        bm25_scores = self._bm25.get_scores(query_tokens)
        bm25_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[:30]
        bm25_docs = [
            (self._make_doc(i), float(bm25_scores[i])) for i in bm25_indices
            if bm25_scores[i] > 0
        ]
        logger.debug(f"BM25 召回 {len(bm25_docs)} 条")

        # 2. Vector 召回 Top30
        vector_docs = self.store.similarity_search(query, k=30)
        logger.debug(f"Vector 召回 {len(vector_docs)} 条")

        # 3. RRF Fusion
        fused = self._rrf_fusion(bm25_docs, vector_docs)
        logger.debug(f"RRF 融合后 {len(fused)} 条")

        # 4. Reranker 精排 → Top5
        if self.reranker and fused:
            fused = self.reranker.rerank(query, fused, top_k=top_k)

        return fused[:top_k]

    def _make_doc(self, idx: int) -> Document:
        """从 BM25 索引构建 Document 对象"""
        return Document(
            page_content=self._chunk_texts[idx],
            metadata={"_file_name": self._chunk_sources[idx], "_source": "bm25"},
        )

    # ── RRF Fusion ──────────────────────────────────────────

    @staticmethod
    def _rrf_fusion(
        bm25_docs: List[tuple],
        vector_docs: List[Document],
        k: int = 60,
    ) -> List[Document]:
        """Reciprocal Rank Fusion

        每个文档的 RRF 分数 = 1/(k + rank_in_bm25) + 1/(k + rank_in_vector)
        按总分降序排列。
        """
        scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        for rank, (doc, _score) in enumerate(bm25_docs):
            fp = _fingerprint(doc)
            scores[fp] = scores.get(fp, 0) + 1.0 / (k + rank)
            doc_map[fp] = doc

        for rank, doc in enumerate(vector_docs):
            fp = _fingerprint(doc)
            scores[fp] = scores.get(fp, 0) + 1.0 / (k + rank)
            if fp not in doc_map:
                doc_map[fp] = doc

        sorted_fps = sorted(scores, key=lambda fp: scores[fp], reverse=True)
        return [doc_map[fp] for fp in sorted_fps]


def _fingerprint(doc: Document) -> str:
    """文档指纹: 用内容前 150 字符去重"""
    return doc.page_content[:150]
