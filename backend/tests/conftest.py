"""pytest fixtures —— 测试用向量库初始化、多文档加载、清理"""
import os
import sys
import json
import asyncio
import shutil
import tempfile
from pathlib import Path
import pytest

# 将 backend 目录加入 sys.path，确保测试能导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.utils.factory import get_embed_model
from app.rag.loader import load_file_sync
from app.rag.text_splitter import DocumentSplitter
from app.rag.retriever import HybridRetriever
from app.core.logger import logger


TEST_COLLECTION = "rag2_test_collection"

# 测试文档配置：(路径, 文档标识, chunk_id前缀)
TEST_DOCS = [
    ("test2.txt", "milk_city", "mc"),           # 牛奶市（项目根目录）
    ("test_doc_ai.txt", "ai_industry", "ai"),    # AI产业（tests/test_data/）
    ("test_doc_env.txt", "env_policy", "env"),   # 双碳政策（tests/test_data/）
]


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def test_cases(test_data_dir):
    """加载对抗测试用例"""
    cases_path = test_data_dir / "test_cases.json"
    if not cases_path.exists():
        pytest.skip("test_cases.json 不存在")
    with open(cases_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def temp_chroma_dir():
    """为测试创建临时ChromaDB目录"""
    tmp = tempfile.mkdtemp(prefix="rag2_test_chroma_")
    yield tmp
    # 清理
    if os.path.exists(tmp):
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="session")
def test_chroma_store(temp_chroma_dir, test_data_dir):
    """创建测试用ChromaDB并加载3篇测试文档（含干扰项）"""
    embed = get_embed_model()

    store = Chroma(
        collection_name=TEST_COLLECTION,
        embedding_function=embed,
        persist_directory=temp_chroma_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )

    splitter = DocumentSplitter()
    total_chunks = 0
    chunk_counter = 0

    for doc_name, source_id, prefix in TEST_DOCS:
        # 确定文档路径
        if doc_name == "test2.txt":
            doc_path = Path(__file__).parent.parent.parent / doc_name
        else:
            doc_path = test_data_dir / doc_name

        if not doc_path.exists():
            logger.warning(f"测试文档不存在，跳过: {doc_path}")
            continue

        # 加载并切分
        docs = load_file_sync(str(doc_path))
        chunks = splitter.split_sync(docs)

        for chunk in chunks:
            chunk.metadata["chunk_id"] = f"{prefix}_{chunk_counter}"
            chunk.metadata["filename"] = doc_name
            chunk.metadata["source"] = source_id
            chunk.metadata["md5"] = f"test_md5_{source_id}"
            chunk_counter += 1

        store.add_documents(chunks)
        total_chunks += len(chunks)
        logger.info(f"测试文档入库: {doc_name} -> {len(chunks)} chunks")

    logger.info(f"测试ChromaDB就绪: {total_chunks} chunks (来源: {len(TEST_DOCS)}篇文档)")

    yield store

    # 清理
    try:
        store.delete_collection()
    except Exception:
        pass


@pytest.fixture(scope="session")
def test_retriever(test_chroma_store):
    """创建测试用HybridRetriever（注入测试ChromaDB）"""
    retriever = HybridRetriever()
    import app.rag.vector_store as vs_module
    original_store = vs_module.vector_store_service._store
    vs_module.vector_store_service._store = test_chroma_store
    yield retriever
    vs_module.vector_store_service._store = original_store
