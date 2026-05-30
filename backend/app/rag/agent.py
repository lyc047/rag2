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
    """搜索知识库获取答案。返回的是可直接呈现给用户的完整答案，不要添加任何前言或修改。"""
    result = await rag_service.query(query, stream=False)
    if isinstance(result, dict):
        answer = result.get("answer", "未找到相关信息")
        # 在答案前加一个指令前缀，告诉Agent这是最终答案
        return f"[以下是搜索到的答案，请直接呈现给用户，不要添加任何前言或修改]\n\n{answer}"
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
async def create_note(title: str, content: str, tags: str = "") -> str:
    """创建新笔记。将重要信息记录到笔记中。tags为标签列表，用逗号分隔，如'工作,学习'。"""
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        async with async_session_factory() as session:
            note = Note(title=title, content=content, tags=json.dumps(tag_list, ensure_ascii=False))
            session.add(note)
            await session.commit()
            await session.refresh(note)
            await vector_store_service.upsert_note(note.id, title, content)
            return f"笔记已创建成功：{note.title} (id: {note.id})"
    except Exception as e:
        logger.error(f"创建笔记失败: {e}", exc_info=True)
        return f"创建笔记失败: {e}"


@tool
async def get_note(note_id: str) -> str:
    """获取指定笔记的完整内容。需要笔记ID。"""
    try:
        async with async_session_factory() as session:
            note = await session.get(Note, note_id)
            if not note:
                return f"笔记 {note_id} 不存在"
            tags = json.loads(note.tags) if note.tags else []
            return f"笔记标题：{note.title}\n标签：{', '.join(tags) if tags else '无'}\n内容：\n{note.content}"
    except Exception as e:
        logger.error(f"获取笔记失败: {e}", exc_info=True)
        return f"获取笔记失败: {e}"


@tool
async def update_note(note_id: str, title: str = "", content: str = "", tags: str = "") -> str:
    """修改笔记。可修改标题、内容和标签，只需填写要修改的字段。tags用逗号分隔。"""
    try:
        async with async_session_factory() as session:
            note = await session.get(Note, note_id)
            if not note:
                return f"笔记 {note_id} 不存在"
            if title:
                note.title = title
            if content:
                note.content = content
            if tags:
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                note.tags = json.dumps(tag_list, ensure_ascii=False)
            await session.commit()
            await session.refresh(note)
            await vector_store_service.upsert_note(note.id, note.title, note.content)
            return f"笔记已更新：{note.title} (id: {note.id})"
    except Exception as e:
        logger.error(f"修改笔记失败: {e}", exc_info=True)
        return f"修改笔记失败: {e}"


@tool
async def delete_note(note_id: str) -> str:
    """删除指定笔记。删除前请先向用户确认。"""
    try:
        async with async_session_factory() as session:
            note = await session.get(Note, note_id)
            if not note:
                return f"笔记 {note_id} 不存在"
            title = note.title
            await session.delete(note)
            await session.commit()
            await vector_store_service.delete_note_vector(note_id)
            return f"笔记「{title}」已删除"
    except Exception as e:
        logger.error(f"删除笔记失败: {e}", exc_info=True)
        return f"删除笔记失败: {e}"


@tool
def get_current_time() -> str:
    """获取当前日期和时间"""
    return datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")


# 工具列表
AGENT_TOOLS = [search_knowledge, search_notes, create_note, get_note, update_note, delete_note, get_current_time]

# Agent系统提示词
AGENT_SYSTEM_PROMPT = """你是智能笔记助手，可以帮助用户：
1. 从知识库中检索和回答问题
2. 搜索和管理用户的笔记（查看、创建、修改、删除）
3. 创建新笔记记录重要信息

## 输出铁律 —— 绝对禁止的行为
- 禁止输出"我正在搜索……""让我查找……""根据搜索结果……""第一步……第二步……"等内部思考过程
- 禁止输出"我需要调用……工具""让我确认……""经过分析……"等元语言
- 禁止在回答中解释你做了什么操作、调用了什么工具
- 禁止在给出答案后追加"如果你还有其他问题……"等冗余客套话
- 你的输出直接就是答案本身，不加前缀、不加后记

## 工具使用规则
- search_knowledge 返回的是已经整理好的完整答案，直接原样呈现给用户，不要在上面加任何前言或总结
- 如果 search_knowledge 返回"未找到"，直接告诉用户知识库中没有相关信息
- 当用户想查找笔记时，使用 search_notes，返回结果中包含笔记ID
- 当用户想看某篇笔记的完整内容时，使用 get_note(note_id)
- 当用户要求记录信息时，使用 create_note 创建笔记
- 当用户要求修改笔记时，使用 update_note，只传需要修改的字段
- 删除笔记前必须先征得用户确认，再使用 delete_note
- 严禁编造知识

当前时间：{current_time}"""


class AgentService:
    """Agent服务 —— 封装Agent创建和调用（LangChain 1.3+ create_agent API）"""

    def __init__(self):
        self.llm = get_chat_model()
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
            if kind == "on_chat_model_stream":
                content = event.get("data", {}).get("chunk", {}).content
                if content:
                    yield {"type": "token", "content": content}
            elif kind == "on_tool_start":
                tool_name = event.get("name", "")
                yield {"type": "tool_start", "tool": tool_name}
            elif kind == "on_tool_end":
                tool_name = event.get("name", "")
                output = event.get("data", {}).get("output", "")
                yield {"type": "tool_end", "tool": tool_name, "output": str(output)[:200]}


# 全局单例
agent_service = AgentService()
