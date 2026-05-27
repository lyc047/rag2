"""文本切片器 —— 使用RecursiveCharacterTextSplitter进行智能分词"""
import asyncio
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config.settings import CHROMA_CHUNK_SIZE, CHROMA_CHUNK_OVERLAP
from app.core.logger import logger


class DocumentSplitter:
    """文档切片器，按段落→句子→字符的优先级切分"""

    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHROMA_CHUNK_SIZE,
            chunk_overlap=CHROMA_CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", "！", "？", "，", " ", ""],
        )

    async def split(self, documents: list[Document]) -> list[Document]:
        """异步切分文档"""
        if not documents:
            return []
        chunks = await asyncio.to_thread(self.splitter.split_documents, documents)
        logger.info(f"文档切分: {len(documents)}篇 -> {len(chunks)}个片段")
        return chunks

    def split_sync(self, documents: list[Document]) -> list[Document]:
        """同步切分文档（多线程用）"""
        if not documents:
            return []
        return self.splitter.split_documents(documents)
