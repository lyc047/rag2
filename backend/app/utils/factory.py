"""模型工厂 —— 创建LLM和嵌入模型实例"""
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI
from app.config.settings import (
    LLM_TYPE, OLLAMA_CHAT_MODEL, OLLAMA_BASE_URL,
    EMBED_MODEL_TYPE, OLLAMA_EMBED_MODEL
)
from app.core.logger import logger

# 全局模型实例（延迟初始化）
chat_model = None
embed_model = None


def get_chat_model():
    """获取LLM聊天模型（带缓存）"""
    global chat_model
    if chat_model is not None:
        return chat_model

    if LLM_TYPE == "DEEPSEEK":
        import os
        chat_model = ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url="https://api.deepseek.com/v1",
            temperature=0.7,
            streaming=True,
        )
        logger.info(f"LLM: DeepSeek (deepseek-chat)")
    else:
        # 默认OLLAMA
        chat_model = ChatOllama(
            model=OLLAMA_CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.7,
        )
        logger.info(f"LLM: Ollama ({OLLAMA_CHAT_MODEL})")
    return chat_model


def get_embed_model():
    """获取嵌入模型（带缓存）"""
    global embed_model
    if embed_model is not None:
        return embed_model

    if EMBED_MODEL_TYPE == "OLLAMA":
        embed_model = OllamaEmbeddings(
            model=OLLAMA_EMBED_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
        logger.info(f"Embed: Ollama ({OLLAMA_EMBED_MODEL})")
    else:
        raise ValueError(f"不支持的嵌入模型类型: {EMBED_MODEL_TYPE}")
    return embed_model
