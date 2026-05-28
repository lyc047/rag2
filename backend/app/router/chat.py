"""AI助手路由 —— Agent对话、会话管理"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.response import success_response
from app.db.database import get_db
from app.schemas.models import ChatRequest
from app.rag.agent import agent_service
from app.services.session_service import session_service
from app.core.logger import logger

router = APIRouter()


@router.post("/query")
async def chat_query(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Agent流式对话 —— SSE返回token和工具调用"""
    # 获取或创建会话，并加载历史消息
    session_id = req.session_id
    history = []
    if session_id:
        session = await session_service.get_session(db, session_id)
        if not session:
            session = await session_service.create_session(db)
            session_id = session.id
        else:
            # 从已有会话中提取历史消息
            for msg in session.messages:
                history.append({"role": msg.role, "content": msg.content})
    else:
        session = await session_service.create_session(db)
        session_id = session.id

    # 保存用户消息
    await session_service.add_message(db, session_id, "user", req.query)

    assistant_content = []

    async def event_stream():
        nonlocal assistant_content
        try:
            async for event in agent_service.chat_stream(req.query, history, req.lang):
                if event["type"] == "token":
                    assistant_content.append(event["content"])
                    yield f"data: {json.dumps({'type': 'token', 'content': event['content']}, ensure_ascii=False)}\n\n"
                elif event["type"] == "tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['tool']}, ensure_ascii=False)}\n\n"
                elif event["type"] == "tool_end":
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['tool'], 'output': event['output']}, ensure_ascii=False)}\n\n"

            # 保存助手回复
            full_answer = "".join(assistant_content)
            if full_answer:
                await session_service.add_message(db, session_id, "assistant", full_answer)

            yield f"data: {json.dumps({'type': 'finish', 'session_id': session_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Agent对话出错: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """获取会话列表"""
    sessions = await session_service.list_sessions(db)
    return success_response(data=[s.model_dump() for s in sessions])


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """获取会话详情（含消息）"""
    session = await session_service.get_session(db, session_id)
    if not session:
        return success_response(data=None)
    return success_response(data=session.model_dump())


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """删除会话"""
    await session_service.delete_session(db, session_id)
    return success_response(message="会话已删除")
