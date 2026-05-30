"""向量库封装 —— ChromaDB操作：增删改查、MD5去重、笔记向量同步"""
import os
import asyncio
import shutil
from datetime import datetime
from typing import Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.config.settings import CHROMA_PERSIST_PATH, CHROMA_COLLECTION, CHROMA_DISTANCE_METRIC, DATA_PATH, CONTENT_TIME_EXTRACTION, CHUNK_STRATEGY
from app.utils.factory import get_embed_model
from app.utils.md5_store import MD5Store
from app.rag.loader import get_file_md5_sync, load_file_sync, get_file_mtime_sync, extract_content_time_range
from app.rag.text_splitter import DocumentSplitter
from app.core.logger import logger


class VectorStoreService:
    """ChromaDB向量库服务 —— 管理知识库文档和笔记的向量存储"""

    def __init__(self):
        self._store: Optional[Chroma] = None
        self._notes_store: Optional[Chroma] = None
        self.md5_store = MD5Store()
        self.splitter = DocumentSplitter(strategy=CHUNK_STRATEGY)

    @property
    def knowledge_store(self) -> Chroma:
        """知识库向量库（延迟初始化）"""
        if self._store is None:
            embed = get_embed_model()
            os.makedirs(CHROMA_PERSIST_PATH, exist_ok=True)
            self._store = Chroma(
                collection_name=CHROMA_COLLECTION,
                embedding_function=embed,
                persist_directory=CHROMA_PERSIST_PATH,
                collection_metadata={"hnsw:space": CHROMA_DISTANCE_METRIC},
            )
            logger.info(f"知识库向量库已初始化: {CHROMA_COLLECTION} ({CHROMA_DISTANCE_METRIC})")
        return self._store

    @property
    def notes_store(self) -> Chroma:
        """笔记向量库（延迟初始化）"""
        if self._notes_store is None:
            embed = get_embed_model()
            os.makedirs(CHROMA_PERSIST_PATH, exist_ok=True)
            self._notes_store = Chroma(
                collection_name=f"{CHROMA_COLLECTION}_notes",
                embedding_function=embed,
                persist_directory=CHROMA_PERSIST_PATH,
                collection_metadata={"hnsw:space": CHROMA_DISTANCE_METRIC},
            )
            logger.info(f"笔记向量库已初始化: {CHROMA_COLLECTION}_notes ({CHROMA_DISTANCE_METRIC})")
        return self._notes_store

    # ==================== 知识库文档操作 ====================
    async def add_document(self, file_path: str, filename: str) -> dict:
        """处理并存储单个文档到知识库"""
        # MD5去重检查
        md5_hex = get_file_md5_sync(file_path)
        if not md5_hex:
            return {"success": False, "filename": filename, "error": "MD5计算失败"}
        if await self.md5_store.exists(md5_hex):
            return {"success": False, "filename": filename, "error": "文档已存在", "skipped": True}

        # 加载文件
        docs = load_file_sync(file_path)
        if not docs:
            return {"success": False, "filename": filename, "error": "文件内容为空"}

        # 切分文档
        chunks = self.splitter.split_sync(docs)
        if not chunks:
            return {"success": False, "filename": filename, "error": "文档切分为空"}

        # 提取时间元数据
        file_mtime = get_file_mtime_sync(file_path)
        uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 从文档内容中提取年份范围（需要原始全文）
        content_time_range = ""
        if CONTENT_TIME_EXTRACTION:
            full_text = " ".join(d.page_content for d in docs)
            content_time_range = extract_content_time_range(full_text)

        # 写入元数据
        for doc in chunks:
            doc.metadata["filename"] = filename
            doc.metadata["md5"] = md5_hex
            doc.metadata["uploaded_at"] = uploaded_at
            if file_mtime:
                doc.metadata["file_mtime"] = file_mtime
            if content_time_range:
                doc.metadata["content_time_range"] = content_time_range

        # 存入向量库
        await asyncio.to_thread(self.knowledge_store.add_documents, chunks)
        await self.md5_store.save(md5_hex, filename)
        logger.info(f"文档已入库: {filename} ({len(chunks)}个片段)")
        return {"success": True, "filename": filename, "md5": md5_hex, "chunk_count": len(chunks)}

    async def add_documents_batch(self, file_paths: list, filenames: dict = None) -> list:
        """批量处理文档"""
        results = []
        for file_path in file_paths:
            filename = (filenames or {}).get(file_path, os.path.basename(file_path))
            result = await self.add_document(file_path, filename)
            results.append(result)
        return results

    async def search_knowledge(self, query: str, top_k: int = 5) -> list[Document]:
        """检索知识库"""
        return await asyncio.to_thread(
            self.knowledge_store.similarity_search, query, k=top_k
        )

    async def delete_document(self, md5_hex: str):
        """删除文档（通过MD5过滤）"""
        store = self.knowledge_store
        results = store.get(where={"md5": md5_hex})
        if results and results.get("ids"):
            store.delete(ids=results["ids"])
        await self.md5_store.delete(md5_hex)

    async def list_documents(self) -> list[dict]:
        """列出所有已入库文档"""
        return await self.md5_store.list_all()

    async def get_document_chunks(self, md5_hex: str) -> list[dict]:
        """获取指定文档的所有切片"""
        store = self.knowledge_store
        results = store.get(where={"md5": md5_hex})
        chunks = []
        if results:
            for i, doc_id in enumerate(results.get("ids", [])):
                chunks.append({
                    "content": results["documents"][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                })
        return chunks

    async def clear_knowledge(self):
        """清空知识库"""
        if self._store:
            self._store.delete_collection()
            self._store = None
        await self.md5_store.clear()
        # 删除持久化目录
        if os.path.exists(CHROMA_PERSIST_PATH):
            shutil.rmtree(CHROMA_PERSIST_PATH)
            os.makedirs(CHROMA_PERSIST_PATH, exist_ok=True)

    # ==================== 笔记向量操作 ====================
    async def upsert_note(self, note_id: str, title: str, content: str):
        """将笔记写入/更新到笔记向量库"""
        # 删除旧的向量
        existing = self.notes_store.get(where={"note_id": note_id})
        if existing and existing.get("ids"):
            self.notes_store.delete(ids=existing["ids"])

        # 创建新向量
        doc = Document(
            page_content=f"{title}\n{content}",
            metadata={"note_id": note_id, "title": title}
        )
        self.notes_store.add_documents([doc])

    async def delete_note_vector(self, note_id: str):
        """从向量库删除笔记"""
        existing = self.notes_store.get(where={"note_id": note_id})
        if existing and existing.get("ids"):
            self.notes_store.delete(ids=existing["ids"])

    async def search_notes(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索笔记"""
        results = self.notes_store.similarity_search(query, k=top_k)
        return [
            {"note_id": doc.metadata.get("note_id", ""), "title": doc.metadata.get("title", ""),
             "content_preview": doc.page_content[:200]}
            for doc in results
        ]


# 全局单例
vector_store_service = VectorStoreService()
