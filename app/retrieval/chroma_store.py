from typing import List, Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document
from loguru import logger
from .embeddings import DashScopeEmbeddings


class ChromaStore:
    """Chroma 向量存储封装

    职责:
    - 管理 Chroma 集合的生命周期
    - 提供文档增删查的简洁接口
    - 延迟初始化，避免模块导入时阻塞
    """

    def __init__(self, collection_name: str = "linux_ops", persist_directory: str = "./chroma_data"):
        self.embeddings = DashScopeEmbeddings()
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._store: Optional[Chroma] = None
        logger.info(f"ChromaStore 初始化, collection={collection_name}")

    def _get_store(self) -> Chroma:
        if self._store is None:
            self._store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
        return self._store

    def add_documents(self, documents: List[Document]) -> List[str]:
        store = self._get_store()
        ids = store.add_documents(documents)
        logger.info(f"向 Chroma 添加 {len(documents)} 个文档")
        return ids

    def similarity_search(self, query: str, k: int = 10) -> List[Document]:
        store = self._get_store()
        return store.similarity_search(query, k=k)

    def delete_by_source(self, source: str):
        store = self._get_store()
        results = store.get(where={"_source": source})
        if results and results.get("ids"):
            store.delete(results["ids"])
            logger.info(f"删除来源 {source} 的 {len(results['ids'])} 个文档")

    def get_retriever(self, k: int = 10):
        store = self._get_store()
        return store.as_retriever(search_kwargs={"k": k})

    def count(self) -> int:
        store = self._get_store()
        return len(store.get()["ids"]) if store.get()["ids"] else 0
