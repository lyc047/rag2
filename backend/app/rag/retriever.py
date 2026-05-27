"""混合检索器 —— BM25关键词检索 + 向量语义检索，动态加权融合"""
import asyncio
from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from app.config.settings import TOP_K, BM25_WEIGHT
from app.rag.vector_store import vector_store_service
from app.core.logger import logger


class HybridRetriever:
    """混合检索：融合BM25（关键词）和向量（语义）检索结果"""

    def __init__(self):
        self.k = TOP_K

    async def retrieve(self, query: str) -> List[Document]:
        """执行混合检索"""
        store = vector_store_service.knowledge_store

        # 获取向量库中所有文档用于构建BM25索引
        all_results = await asyncio.to_thread(store.get)
        all_docs = []
        if all_results and all_results.get("documents"):
            for i, doc_text in enumerate(all_results["documents"]):
                metadata = all_results["metadatas"][i] if all_results.get("metadatas") else {}
                all_docs.append(Document(page_content=doc_text, metadata=metadata))

        if not all_docs:
            return []

        # BM25关键词检索
        bm25_retriever = BM25Retriever.from_documents(all_docs)
        bm25_retriever.k = self.k
        bm25_results = await asyncio.to_thread(bm25_retriever.invoke, query)

        # 向量语义检索
        vector_results = await asyncio.to_thread(
            store.similarity_search, query, k=self.k
        )

        # 加权融合（向量权重更高）
        return self._merge_results(vector_results, bm25_results)

    def _merge_results(self, vector_docs: List[Document], bm25_docs: List[Document]) -> List[Document]:
        """融合两路检索结果 —— 向量结果优先排列，BM25补充不重复的"""
        seen = set()
        merged = []

        # 向量结果先放入
        for doc in vector_docs:
            key = doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                merged.append(doc)

        # BM25结果补充（去重后）
        for doc in bm25_docs:
            key = doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                merged.append(doc)

        return merged[:self.k]
