"""Pydantic数据模型 —— 请求/响应校验"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 笔记 ====================
class NoteCreate(BaseModel):
    """创建笔记请求"""
    title: str = Field(default="未命名笔记", max_length=200)
    content: str = Field(default="")
    tags: List[str] = Field(default_factory=list)


class NoteUpdate(BaseModel):
    """更新笔记请求"""
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class NoteResponse(BaseModel):
    """笔记响应"""
    id: str
    title: str
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class NoteListItem(BaseModel):
    """笔记列表项 —— 不含完整内容"""
    id: str
    title: str
    content_preview: str  # 内容前100字符
    tags: List[str]
    created_at: datetime
    updated_at: datetime


# ==================== 会话 ====================
class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    role: str
    content: str
    created_at: datetime


class SessionDetailResponse(BaseModel):
    """会话详情 —— 含消息列表"""
    id: str
    title: str
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime


# ==================== 聊天 ====================
class ChatRequest(BaseModel):
    """聊天请求"""
    query: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None
    lang: Optional[str] = None


# ==================== 通用 ====================
class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[str] = Field(..., min_length=1, max_length=200)
    def __init__(self, **data):
        super().__init__(**data)
        self.ids = list(dict.fromkeys(self.ids))  # 自动去重


# ==================== 知识库 ====================
class DocumentInfo(BaseModel):
    """文档基本信息"""
    filename: str
    md5: str
    chunk_count: int
    created_at: Optional[str] = None


class ChunkDetail(BaseModel):
    """文档切片详情"""
    content: str
    metadata: dict


# ==================== 通用 ====================
class PageRequest(BaseModel):
    """分页请求"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SuccessResponse(BaseModel):
    """成功响应"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
