"""文本切片器 —— 支持递归字符分割和Markdown结构感知语义分割"""
import asyncio
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config.settings import CHROMA_CHUNK_SIZE, CHROMA_CHUNK_OVERLAP
from app.core.logger import logger


# Markdown标题标记（按层级从低到高排列，确保优先在大标题处断）
_MD_HEADING_SEPARATORS = [
    "\n#### ", "\n### ", "\n## ", "\n# ",
    "\n####", "\n###", "\n##", "\n#",
]


class DocumentSplitter:
    """文档切片器 —— 支持递归字符分割与Markdown结构感知语义分割"""

    def __init__(self, strategy: str = "recursive"):
        """
        Args:
            strategy: 切分策略
                - "recursive": 默认递归字符分割（按段落→句子→字符优先级）
                - "semantic": Markdown结构感知分割（在标题边界优先断句）
        """
        self.strategy = strategy
        separators = self._build_separators(strategy)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHROMA_CHUNK_SIZE,
            chunk_overlap=CHROMA_CHUNK_OVERLAP,
            separators=separators,
        )

    @staticmethod
    def _build_separators(strategy: str) -> list[str]:
        """根据策略构建分隔符优先级列表"""
        # 基础分隔符（从粗到细）
        base_separators = ["\n\n", "\n", "。", ".", "！", "？", "，", " ", ""]

        if strategy == "semantic":
            # Markdown标题作为最高优先级的断点
            return _MD_HEADING_SEPARATORS + base_separators
        else:
            return base_separators

    async def split(self, documents: list[Document]) -> list[Document]:
        """异步切分文档"""
        if not documents:
            return []
        chunks = await asyncio.to_thread(self.splitter.split_documents, documents)
        logger.info(f"文档切分({self.strategy}): {len(documents)}篇 -> {len(chunks)}个片段")
        return chunks

    def split_sync(self, documents: list[Document]) -> list[Document]:
        """同步切分文档（多线程用）"""
        if not documents:
            return []
        chunks = self.splitter.split_documents(documents)
        logger.info(f"文档切分({self.strategy}): {len(documents)}篇 -> {len(chunks)}个片段")
        return chunks
