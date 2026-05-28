"""笔记路由 —— CRUD + 关键字搜索"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.response import success_response
from app.db.database import get_db
from app.schemas.models import NoteCreate, NoteUpdate, PageRequest
from app.services.note_service import note_service

router = APIRouter()


@router.get("/search/{query}")
async def search_notes(query: str, db: AsyncSession = Depends(get_db)):
    """关键字搜索笔记 —— 标题 > 标签 > 正文"""
    items = await note_service.search(db, query)
    return success_response(data=[i.model_dump() for i in items])


@router.post("")
async def create_note(data: NoteCreate, db: AsyncSession = Depends(get_db)):
    """创建笔记"""
    note = await note_service.create(db, data)
    return success_response(data=note.model_dump())


@router.put("/{note_id}")
async def update_note(note_id: str, data: NoteUpdate, db: AsyncSession = Depends(get_db)):
    """更新笔记"""
    note = await note_service.update(db, note_id, data)
    if not note:
        return success_response(data=None)
    return success_response(data=note.model_dump())


@router.delete("/{note_id}")
async def delete_note(note_id: str, db: AsyncSession = Depends(get_db)):
    """删除笔记"""
    ok = await note_service.delete(db, note_id)
    return success_response(message="已删除" if ok else "笔记不存在")


@router.get("/{note_id}")
async def get_note(note_id: str, db: AsyncSession = Depends(get_db)):
    """获取笔记详情"""
    note = await note_service.get(db, note_id)
    if not note:
        return success_response(data=None)
    return success_response(data=note.model_dump())


@router.get("")
async def list_notes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """分页获取笔记列表"""
    items, total = await note_service.list(db, page, page_size, category)
    return success_response(data={
        "items": [i.model_dump() for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })
