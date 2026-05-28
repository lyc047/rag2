"""LangChain Agent —— 工具调用链，整合知识库检索和笔记功能（适配LangChain 1.3+）"""
import json
from datetime import datetime
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from app.utils.factory import get_chat_model
from app.rag.rag_service import rag_service
from app.rag.vector_store import vector_store_service
from app.db.database import async_session_factory
from app.models.note import Note
from app.core.logger import logger


# ==================== Agent工具定义 ====================
@tool
async def search_knowledge(query: str) -> str:
    """搜索知识库中的文档内容。当用户询问知识库中存储的文档相关信息时使用此工具。"""
    result = await rag_service.query(query, stream=False)
    if isinstance(result, dict):
        return result.get("answer", "未找到相关信息")
    return "搜索失败"


@tool
async def search_notes(query: str) -> str:
    """搜索用户笔记。当用户想查找自己的笔记内容时使用。"""
    notes = await vector_store_service.search_notes(query, top_k=5)
    if not notes:
        return "没有找到相关笔记"
    lines = ["找到以下相关笔记："]
    for n in notes:
        lines.append(f"- [{n['title']}](id:{n['note_id']}): {n['content_preview'][:100]}")
    return "\n".join(lines)


@tool
async def create_note(title: str, content: str) -> str:
    """创建新笔记。将重要信息记录到笔记中。"""
    try:
        async with async_session_factory() as session:
            note = Note(title=title, content=content, tags=json.dumps([], ensure_ascii=False))
            session.add(note)
            await session.commit()
            await session.refresh(note)
            await vector_store_service.upsert_note(note.id, title, content)
            return f"笔记已创建成功：{note.title} (id: {note.id})"
    except Exception as e:
        return f"创建笔记失败: {e}"


@tool
def get_current_time() -> str:
    """获取当前日期和时间"""
    return datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")


# 工具列表
AGENT_TOOLS = [search_knowledge, search_notes, create_note, get_current_time]

# Agent系统提示词
AGENT_SYSTEM_PROMPT = """你是智能笔记助手，可以帮助用户：
1. 从知识库中检索和回答问题
2. 搜索和管理用户的笔记
3. 创建新笔记记录重要信息

使用工具体系回答用户问题。记住：
- 当用户询问知识相关问题时，优先使用 search_knowledge 搜索知识库
- 当用户想查找笔记时，使用 search_notes
- 当用户要求记录信息时，使用 create_note 创建笔记
- 严禁编造知识，如果检索不到就说没找到

当前时间：{current_time}"""


class AgentService:
    """Agent服务 —— 封装Agent创建和调用（LangChain 1.3+ create_agent API）"""

    def __init__(self):
        self.llm = get_chat_model()
        # 使用LangChain 1.3新API创建Agent
        self.agent = create_agent(
            model=self.llm,
            tools=AGENT_TOOLS,
            system_prompt=AGENT_SYSTEM_PROMPT.format(
                current_time=datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
            ),
        )

    def _build_messages(self, query: str, chat_history: list = None, lang: str = None) -> list:
        """构建消息列表 —— 将历史记录转为LangChain消息格式"""
        messages = []
        if lang == 'en':
            messages.append(SystemMessage(content="You MUST respond in English only. Never use Chinese. Always reply in natural English."))
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=query))
        return messages

    async def chat(self, query: str, chat_history: list = None, lang: str = None) -> dict:
        """执行Agent对话"""
        messages = self._build_messages(query, chat_history, lang)
        result = await self.agent.ainvoke({"messages": messages})
        # 提取最后一条AI消息作为回答
        output = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                output = msg.content
                break
        return {"answer": output}

    async def chat_stream(self, query: str, chat_history: list = None, lang: str = None):
        """流式Agent对话 —— 逐token返回"""
        messages = self._build_messages(query, chat_history, lang)
        async for event in self.agent.astream_events(
            {"messages": messages},
            version="v2",
        ):
            kind = event.get("event")
            # 推送LLM输出的token
            if kind == "on_chat_model_stream":
                content = event.get("data", {}).get("chunk", {}).content
                if content:
                    yield {"type": "token", "content": content}
            # 推送工具调用信息
            elif kind == "on_tool_start":
                tool_name = event.get("name", "")
                yield {"type": "tool_start", "tool": tool_name}
            elif kind == "on_tool_end":
                tool_name = event.get("name", "")
                output = event.get("data", {}).get("output", "")
                yield {"type": "tool_end", "tool": tool_name, "output": str(output)[:200]}


# 全局单例
agent_service = AgentService()
