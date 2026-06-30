from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from app.config import config


class DocumentSplitter:
    """文档切分器

    使用 RecursiveCharacterTextSplitter 递归分割文本:
    1. 优先按段落分割
    2. 段落太长则按句子分割
    3. 句子太长则按字符分割
    保证切分后的片段语义完整。
    """

    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
        logger.info(f"DocumentSplitter: chunk_size={self.chunk_size}, overlap={self.chunk_overlap}")

    def split_documents(self, documents: List[Document]) -> List[Document]:
        return self.splitter.split_documents(documents)

    def split_text(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        return self.splitter.create_documents([text], metadatas=[metadata or {}])
