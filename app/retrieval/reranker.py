from typing import List, Optional
from langchain_core.documents import Document
from loguru import logger


class Reranker:
    """重排序器

    使用交叉编码器（Cross-Encoder）对 Chroma 召回的候选文档进行精确重排。
    相比向量余弦相似度，交叉编码器能更准确地判断文本对的相关性。

    如果 sentence-transformers 没有安装，自动跳过重排，不阻塞主流程。
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None
        self._available = False
        self._init_model()

    def _init_model(self):
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
            self._available = True
            logger.info(f"Reranker 加载完成: {self.model_name}")
        except Exception as e:
            logger.warning(f"Reranker 不可用 ({e})，跳过重排")

    def rerank(self, query: str, documents: List[Document], top_k: Optional[int] = None) -> List[Document]:
        if not self._available or not documents:
            return documents

        pairs = [[query, doc.page_content] for doc in documents]
        scores = self._model.predict(pairs)

        scored = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        result = [doc for _, doc in scored]

        if top_k:
            result = result[:top_k]
        return result
