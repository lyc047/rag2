"""混合检索器 —— BM25关键词检索 + 向量语义检索，RRF加权融合 + 精确短语匹配奖励"""
import asyncio
import re
from typing import List
import numpy as np
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from app.config.settings import TOP_K, RETRIEVAL_K, BM25_WEIGHT, VECTOR_WEIGHT, SIMILARITY_THRESHOLD
from app.rag.vector_store import vector_store_service
from app.core.logger import logger


def _tokenize(text: str) -> list[str]:
    """中文友好分词 —— 单字符切分，适配BM25"""
    return list(text)


def _extract_key_phrases(query: str) -> list[str]:
    """从查询中提取关键短语（长度>=2的中文/英文词），用于精确匹配加权"""
    # 提取中文连续字符（>=2字）
    cn_phrases = re.findall(r'[一-鿿]{2,}', query)
    # 提取英文连续字符（>=3字母，过滤常见短词）
    en_phrases = re.findall(r'[a-zA-Z]{3,}', query)
    phrases = cn_phrases + en_phrases
    # 去重
    return list(dict.fromkeys(phrases))


class HybridRetriever:
    """混合检索：RRF融合BM25（关键词）和向量（语义）检索结果，支持阈值过滤和BM25缓存"""

    def __init__(self):
        self.k = TOP_K
        self.retrieval_k = max(RETRIEVAL_K, TOP_K)  # 初检召回数，至少>=TOP_K
        self.vector_weight = VECTOR_WEIGHT
        self.bm25_weight = BM25_WEIGHT
        self.similarity_threshold = SIMILARITY_THRESHOLD
        # BM25索引缓存
        self._cached_texts: list[str] = []
        self._cached_docs: list[Document] = []
        self._bm25: BM25Okapi | None = None
        self._cached_count = -1

    async def _ensure_bm25_cache(self):
        """检查并重建BM25索引缓存（基于文档数量变化自动失效）"""
        store = vector_store_service.knowledge_store
        all_results = await asyncio.to_thread(store.get)

        current_count = 0
        all_docs = []
        all_texts = []
        if all_results and all_results.get("documents"):
            current_count = len(all_results["documents"])
            for i, doc_text in enumerate(all_results["documents"]):
                metadata = all_results["metadatas"][i] if all_results.get("metadatas") else {}
                all_docs.append(Document(page_content=doc_text, metadata=metadata))
                all_texts.append(doc_text)

        if current_count == self._cached_count and self._bm25 is not None:
            return  # 缓存有效

        self._cached_docs = all_docs
        self._cached_texts = all_texts
        self._cached_count = current_count
        if all_texts:
            tokenized = [_tokenize(t) for t in all_texts]
            self._bm25 = BM25Okapi(tokenized)
            logger.info(f"BM25索引已重建: {current_count}个文档")
        else:
            self._bm25 = None

    async def retrieve(self, query: str) -> List[Document]:
        """执行混合检索 —— RRF加权融合"""
        await self._ensure_bm25_cache()

        if not self._cached_docs or self._bm25 is None:
            return []

        store = vector_store_service.knowledge_store

        # 1. 向量语义检索（带分数，L2/余弦距离，越小越相似）
        vector_with_scores = await asyncio.to_thread(
            store.similarity_search_with_score, query, k=self.retrieval_k,
        )

        # 2. BM25关键词检索（带分数）
        tokenized_query = _tokenize(query)
        bm25_scores = self._bm25.get_scores(tokenized_query)
        bm25_top_indices = np.argsort(bm25_scores)[::-1][:self.retrieval_k]

        # 3. 构建 (doc, rank) 映射
        vector_ranks: dict[str, tuple[Document, int]] = {}
        rank = 1
        for doc, score in vector_with_scores:
            if self.similarity_threshold is not None and score > self.similarity_threshold:
                continue
            key = doc.page_content[:100]
            if key not in vector_ranks:
                vector_ranks[key] = (doc, rank)
                rank += 1

        bm25_ranks: dict[str, tuple[Document, int]] = {}
        for rank, idx in enumerate(bm25_top_indices, start=1):
            doc = self._cached_docs[idx]
            key = doc.page_content[:100]
            if key not in bm25_ranks:
                bm25_ranks[key] = (doc, rank)

        # 4. RRF加权融合
        k_rrf = 60  # RRF平滑常数
        rrf_scores: dict[str, float] = {}
        all_keys = set(vector_ranks.keys()) | set(bm25_ranks.keys())

        for key in all_keys:
            score = 0.0
            if key in vector_ranks:
                score += self.vector_weight / (k_rrf + vector_ranks[key][1])
            if key in bm25_ranks:
                score += self.bm25_weight / (k_rrf + bm25_ranks[key][1])
            rrf_scores[key] = score

        # 4.5 精确短语匹配奖励
        key_phrases = _extract_key_phrases(query)
        if key_phrases:
            # 统计每个短语在候选chunk中的出现率（用于稀有度加权）
            for phrase in key_phrases:
                phrase_hit_count = 0
                for key in all_keys:
                    doc = (vector_ranks.get(key) or bm25_ranks.get(key))[0]
                    if phrase in doc.page_content:
                        phrase_hit_count += 1
                # 稀有短语（出现在<30%的chunk中）获得更高奖励
                rarity = max(1.0 - (phrase_hit_count / max(len(all_keys), 1)), 0.3)
                for key in all_keys:
                    doc = (vector_ranks.get(key) or bm25_ranks.get(key))[0]
                    if phrase in doc.page_content:
                        rrf_scores[key] *= (1.0 + 0.5 * rarity)  # 最高1.5x，最低1.15x

        # 5. 按RRF分数排序
        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)

        # 6. 构建最终结果
        merged: list[Document] = []
        for key in sorted_keys[:self.k]:
            doc, _ = vector_ranks.get(key) or bm25_ranks.get(key) or (None, None)
            if doc:
                merged.append(doc)

        logger.info(
            f"RRF融合检索: 向量{len(vector_ranks)}个 + BM25{len(bm25_ranks)}个 "
            f"→ 融合{len(merged)}个 (query={query[:40]}...)"
        )
        return merged
