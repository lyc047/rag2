"""RAG查询服务 —— 检索知识库文档并生成回答"""
from langchain_core.prompts import ChatPromptTemplate
from app.utils.factory import get_chat_model
from app.rag.retriever import HybridRetriever
from app.rag.vector_store import vector_store_service
from app.core.logger import logger

# RAG提示词模板
RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是知识库助手，请根据以下检索到的文档片段回答用户问题。
如果文档中没有相关信息，请如实告知。回答时引用文档中的具体内容。
严禁根据你的训练数据编造信息。"""),
    ("user", "参考资料：\n{context}\n\n用户问题：{question}")
])


class RAGService:
    """RAG查询服务 —— 检索 + 生成"""

    def __init__(self):
        self.retriever = HybridRetriever()
        self.model = get_chat_model()
        self.chain = RAG_PROMPT | self.model

    async def query(self, question: str, stream: bool = False):
        """执行RAG查询 —— 先检索再生成"""
        # 检索相关文档
        docs = await self.retriever.retrieve(question)
        if not docs:
            docs = await vector_store_service.search_knowledge(question)

        context = "\n\n---\n".join([d.page_content for d in docs]) if docs else "暂无相关文档"

        if stream:
            # 流式返回
            return self.chain.astream({"context": context, "question": question})
        else:
            # 非流式返回
            result = await self.chain.ainvoke({"context": context, "question": question})
            return {"answer": result.content, "sources": [d.metadata for d in docs]}


# 全局单例
rag_service = RAGService()
