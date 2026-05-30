"""AI助手路由 —— Agent对话、会话管理"""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.response import success_response
from app.db.database import get_db
from app.schemas.models import ChatRequest, BatchDeleteRequest
from app.rag.agent import agent_service
from app.rag.rag_service import rag_service
from app.services.session_service import session_service
from app.core.logger import logger

router = APIRouter()


@router.post("/query")
async def chat_query(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Agent流式对话 —— 先内部完成推理，清洗后再流式输出干净答案"""
    session_id = req.session_id
    history = []
    if session_id:
        session = await session_service.get_session(db, session_id)
        if not session:
            session = await session_service.create_session(db)
            session_id = session.id
        else:
            for msg in session.messages:
                history.append({"role": msg.role, "content": msg.content})
    else:
        session = await session_service.create_session(db)
        session_id = session.id

    # 保存用户消息并立即提交，释放SQLite写锁供Agent工具使用
    await session_service.add_message(db, session_id, "user", req.query)
    await db.commit()

    async def event_stream():
        try:
            # 阶段1：静默执行Agent推理，收集完整输出（不向前端发送中间token）
            raw_parts = []
            search_result = None  # 捕获 search_knowledge 工具的直接返回

            async for event in agent_service.chat_stream(req.query, history, req.lang):
                if event["type"] == "token":
                    raw_parts.append(event["content"])
                elif event["type"] == "tool_end" and event["tool"] == "search_knowledge":
                    # 捕获知识搜索的原始输出（已经是清洗过的）
                    tool_output = event.get("output", "")
                    if tool_output and "未找到" not in tool_output:
                        search_result = tool_output

            # 阶段2：确定最终答案
            raw_answer = "".join(raw_parts)

            # 如果Agent调用了search_knowledge且返回了有效结果，优先使用工具输出
            if search_result:
                # 去掉工具输出中的指令前缀
                prefix = "[以下是搜索到的答案，请直接呈现给用户，不要添加任何前言或修改]\n\n"
                if search_result.startswith(prefix):
                    search_result = search_result[len(prefix):]
                final_answer = search_result
            else:
                final_answer = raw_answer

            # 阶段3：清洗最终答案（剥离任何残留的推理过程）
            if final_answer.strip():
                try:
                    final_answer = await rag_service._polish_answer(final_answer, req.query)
                except Exception:
                    pass

            # 阶段4：保存到数据库
            if final_answer.strip():
                await session_service.add_message(db, session_id, "assistant", final_answer)
                await db.commit()
            else:
                final_answer = "抱歉，未能生成回答，请稍后重试。"

            # 阶段5：将清洗后的答案逐字流式输出给前端（模拟打字效果）
            yield f"data: {json.dumps({'type': 'token', 'content': final_answer}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'finish', 'session_id': session_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Agent对话出错: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """获取会话列表"""
    sessions = await session_service.list_sessions(db)
    return success_response(data=[s.model_dump() for s in sessions])


@router.delete("/sessions")
async def delete_all_sessions(db: AsyncSession = Depends(get_db)):
    """删除全部会话"""
    count = await session_service.delete_all_sessions(db)
    await db.commit()
    return success_response(message=f"已删除 {count} 个会话", data={"deleted": count})


@router.post("/sessions/batch-delete")
async def batch_delete_sessions(req: BatchDeleteRequest, db: AsyncSession = Depends(get_db)):
    """批量删除会话"""
    count = await session_service.delete_batch(db, req.ids)
    await db.commit()
    return success_response(message=f"已删除 {count} 个会话", data={"deleted": count})


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
