"""笔记服务 —— CRUD + 语义搜索，SQLite存储 + ChromaDB向量同步"""
import json
from typing import Optional, List
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.note import Note
from app.rag.vector_store import vector_store_service
from app.schemas.models import NoteCreate, NoteUpdate, NoteResponse, NoteListItem
from app.core.logger import logger


class NoteService:
    """笔记业务逻辑 —— 数据库操作 + 向量同步"""

    async def create(self, db: AsyncSession, note_data: NoteCreate) -> NoteResponse:
        """创建笔记 —— 写入数据库并同步向量"""
        note = Note(
            title=note_data.title,
            content=note_data.content,
            tags=json.dumps(note_data.tags, ensure_ascii=False),
        )
        db.add(note)
        await db.flush()
        await db.refresh(note)

        # 异步同步到向量库（不阻塞主流程）
        try:
            await vector_store_service.upsert_note(note.id, note.title, note.content)
        except Exception as e:
            logger.error(f"笔记向量同步失败: {e}")

        logger.info(f"笔记已创建: {note.title} ({note.id[:8]}...)")
        return self._to_response(note)

    async def update(self, db: AsyncSession, note_id: str, data: NoteUpdate) -> Optional[NoteResponse]:
        """更新笔记"""
        note = await db.get(Note, note_id)
        if not note:
            return None

        if data.title is not None:
            note.title = data.title
        if data.content is not None:
            note.content = data.content
        if data.tags is not None:
            note.tags = json.dumps(data.tags, ensure_ascii=False)

        await db.flush()
        await db.refresh(note)

        # 同步向量
        try:
            await vector_store_service.upsert_note(note.id, note.title, note.content)
        except Exception as e:
            logger.error(f"笔记向量更新失败: {e}")

        return self._to_response(note)

    async def delete(self, db: AsyncSession, note_id: str) -> bool:
        """删除笔记"""
        note = await db.get(Note, note_id)
        if not note:
            return False
        await db.delete(note)
        await db.flush()

        # 删除向量
        try:
            await vector_store_service.delete_note_vector(note_id)
        except Exception as e:
            logger.error(f"笔记向量删除失败: {e}")
        return True

    async def get(self, db: AsyncSession, note_id: str) -> Optional[NoteResponse]:
        """获取单篇笔记详情"""
        note = await db.get(Note, note_id)
        if not note:
            return None
        return self._to_response(note)

    async def list(self, db: AsyncSession, page: int = 1, page_size: int = 20,
                   category: str = None) -> tuple[List[NoteListItem], int]:
        """分页获取笔记列表"""
        # 总数查询
        count_stmt = select(func.count(Note.id))
        if category:
            count_stmt = count_stmt.where(Note.tags.contains(category))
        total = (await db.execute(count_stmt)).scalar() or 0

        # 列表查询
        stmt = select(Note).order_by(Note.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        if category:
            stmt = stmt.where(Note.tags.contains(category))
        result = await db.execute(stmt)
        notes = result.scalars().all()

        items = [self._to_list_item(note) for note in notes]
        return items, total

    async def search(self, db: AsyncSession, query: str,
                     category: str = None) -> List[NoteListItem]:
        """关键字搜索笔记 —— 标题 > 标签 > 正文 优先级排序，取 top 3"""
        sql = text("""
            SELECT *, CASE
                WHEN title LIKE :q THEN 1
                WHEN tags LIKE :q THEN 2
                WHEN content LIKE :q THEN 3
                ELSE 4
            END AS priority
            FROM notes
            WHERE (title LIKE :q OR tags LIKE :q OR content LIKE :q)
        """ + (" AND tags LIKE :cat" if category else "") + """
            ORDER BY priority, updated_at DESC
            LIMIT 3
        """)
        like = f"%{query}%"
        params = {"q": like}
        if category:
            params["cat"] = f"%{category}%"
        result = await db.execute(sql, params)
        rows = result.fetchall()
        return [NoteListItem(
            id=row.id,
            title=row.title,
            content_preview=row.content[:100] if row.content else "",
            tags=json.loads(row.tags) if row.tags else [],
            created_at=row.created_at,
            updated_at=row.updated_at,
        ) for row in rows]

    def _to_response(self, note: Note) -> NoteResponse:
        """ORM模型 -> 响应模型"""
        tags = []
        if note.tags:
            try:
                tags = json.loads(note.tags)
            except json.JSONDecodeError:
                tags = []
        return NoteResponse(
            id=note.id,
            title=note.title,
            content=note.content,
            tags=tags,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    def _to_list_item(self, note: Note) -> NoteListItem:
        """ORM模型 -> 列表项模型（不含完整内容）"""
        tags = []
        if note.tags:
            try:
                tags = json.loads(note.tags)
            except json.JSONDecodeError:
                tags = []
        return NoteListItem(
            id=note.id,
            title=note.title,
            content_preview=note.content[:100] if note.content else "",
            tags=tags,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )


# 全局单例
note_service = NoteService()
