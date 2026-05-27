"""会话服务 —— 聊天会话和消息的CRUD"""
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chat_history import ChatSession, ChatMessage
from app.schemas.models import SessionResponse, SessionDetailResponse, MessageResponse
from app.core.logger import logger


class SessionService:
    """聊天会话管理"""

    async def create_session(self, db: AsyncSession, title: str = "新对话") -> SessionResponse:
        """创建新会话"""
        session = ChatSession(title=title)
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return SessionResponse(
            id=session.id, title=session.title,
            created_at=session.created_at, updated_at=session.updated_at,
        )

    async def get_session(self, db: AsyncSession, session_id: str) -> Optional[SessionDetailResponse]:
        """获取会话详情（含消息列表）"""
        stmt = select(ChatSession).where(ChatSession.id == session_id).options(selectinload(ChatSession.messages))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            return None
        return SessionDetailResponse(
            id=session.id, title=session.title,
            messages=[MessageResponse(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
                      for m in session.messages],
            created_at=session.created_at, updated_at=session.updated_at,
        )

    async def list_sessions(self, db: AsyncSession) -> list[SessionResponse]:
        """获取会话列表，按更新时间降序"""
        stmt = select(ChatSession).order_by(desc(ChatSession.updated_at))
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        return [SessionResponse(id=s.id, title=s.title, created_at=s.created_at, updated_at=s.updated_at)
                for s in sessions]

    async def add_message(self, db: AsyncSession, session_id: str, role: str, content: str) -> MessageResponse:
        """向会话添加消息"""
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        await db.flush()
        await db.refresh(msg)

        # 更新会话时间戳
        session = await db.get(ChatSession, session_id)
        if session:
            session.updated_at = msg.created_at
            # 自动用第一条用户消息作为标题
            if session.title == "新对话" and role == "user":
                session.title = content[:30]

        return MessageResponse(id=msg.id, role=msg.role, content=msg.content, created_at=msg.created_at)

    async def delete_session(self, db: AsyncSession, session_id: str) -> bool:
        """删除会话（消息级联删除）"""
        session = await db.get(ChatSession, session_id)
        if not session:
            return False
        await db.delete(session)
        await db.flush()
        return True


# 全局单例
session_service = SessionService()
