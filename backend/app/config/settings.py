"""全局配置 —— 从.env文件加载所有配置项"""
import os
from dotenv import load_dotenv

# 加载项目根目录下的.env文件
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))


# ==================== LLM配置 ====================
LLM_TYPE = os.getenv("LLM_TYPE", "OLLAMA")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ==================== 嵌入模型配置 ====================
EMBED_MODEL_TYPE = os.getenv("EMBED_MODEL_TYPE", "OLLAMA")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b")

# ==================== 数据库配置 ====================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/rag2.db")

# ==================== ChromaDB向量库配置 ====================
CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "data/chromadb")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "rag2_collection")
CHROMA_CHUNK_SIZE = int(os.getenv("CHROMA_CHUNK_SIZE", "500"))
CHROMA_CHUNK_OVERLAP = int(os.getenv("CHROMA_CHUNK_OVERLAP", "50"))
CHROMA_DISTANCE_METRIC = os.getenv("CHROMA_DISTANCE_METRIC", "cosine")  # l2 / cosine / ip

# ==================== 知识库配置 ====================
DATA_PATH = os.getenv("DATA_PATH", "data/knowledge")
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".pptx", ".docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

# ==================== 检索配置 ====================
TOP_K = int(os.getenv("TOP_K", "5"))
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "20"))  # 初检召回数（>TOP_K，用于RRF融合候选池）
BM25_WEIGHT = float(os.getenv("BM25_WEIGHT", "0.3"))  # BM25在RRF中的权重
VECTOR_WEIGHT = float(os.getenv("VECTOR_WEIGHT", "0.7"))  # 向量检索在RRF中的权重
SIMILARITY_THRESHOLD = os.getenv("SIMILARITY_THRESHOLD")  # 相似度阈值（L2/余弦距离上限），None=不过滤
if SIMILARITY_THRESHOLD is not None:
    SIMILARITY_THRESHOLD = float(SIMILARITY_THRESHOLD)

# ==================== 服务配置 ====================
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
