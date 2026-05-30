"""文件加载器 —— 支持PDF/TXT/DOCX/MD/PPTX格式，异步+同步双版本"""
import os
import re
import hashlib
import asyncio
from datetime import datetime
import aiofiles
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader, Docx2txtLoader
)
from app.core.logger import logger


# ==================== MD5计算 ====================
async def get_file_md5(file_path: str) -> str:
    """异步计算文件MD5"""
    md5_obj = hashlib.md5()
    chunk_size = 1024
    try:
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(chunk_size):
                md5_obj.update(chunk)
    except Exception as e:
        logger.error(f"MD5计算失败: {file_path} -> {e}")
        return ""
    return md5_obj.hexdigest()


def get_file_md5_sync(file_path: str) -> str:
    """同步计算文件MD5"""
    md5_obj = hashlib.md5()
    chunk_size = 1024
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)
    except Exception as e:
        logger.error(f"MD5计算失败: {file_path} -> {e}")
        return ""
    return md5_obj.hexdigest()


# ==================== 文件加载器(异步) ====================
async def pdf_loader(file_path: str) -> list[Document]:
    """加载PDF文件"""
    try:
        loader = PyPDFLoader(file_path)
        return await asyncio.to_thread(loader.load)
    except Exception as e:
        logger.error(f"PDF加载失败: {file_path} -> {e}")
        return []


async def txt_loader(file_path: str) -> list[Document]:
    """加载TXT文件，支持UTF-8和GBK编码"""
    for encoding in ["utf-8", "gbk"]:
        try:
            loader = TextLoader(file_path, encoding=encoding)
            return await asyncio.to_thread(loader.load)
        except Exception:
            continue
    return []


async def docx_loader(file_path: str) -> list[Document]:
    """加载DOCX文件"""
    try:
        loader = Docx2txtLoader(file_path)
        return await asyncio.to_thread(loader.load)
    except Exception as e:
        logger.error(f"DOCX加载失败: {file_path} -> {e}")
        return []


async def md_loader(file_path: str) -> list[Document]:
    """加载Markdown文件"""
    try:
        loader = UnstructuredMarkdownLoader(file_path, mode="single")
        return await asyncio.to_thread(loader.load)
    except Exception as e:
        logger.error(f"MD加载失败: {file_path} -> {e}")
        return []


async def pptx_loader(file_path: str) -> list[Document]:
    """加载PPTX文件"""
    try:
        loader = UnstructuredPowerPointLoader(file_path, mode="single")
        return await asyncio.to_thread(loader.load)
    except Exception as e:
        logger.error(f"PPTX加载失败: {file_path} -> {e}")
        return []


async def load_file(file_path: str) -> list[Document]:
    """根据扩展名路由到对应加载器"""
    ext = os.path.splitext(file_path)[1].lower()
    loaders = {
        ".pdf": pdf_loader,
        ".txt": txt_loader,
        ".docx": docx_loader,
        ".md": md_loader,
        ".pptx": pptx_loader,
    }
    loader = loaders.get(ext)
    if loader:
        return await loader(file_path)
    return []


# ==================== 文件加载器(同步，多线程用) ====================
def pdf_loader_sync(file_path: str) -> list[Document]:
    try:
        return PyPDFLoader(file_path).load()
    except Exception as e:
        logger.error(f"PDF加载失败: {file_path} -> {e}")
        return []


def txt_loader_sync(file_path: str) -> list[Document]:
    for encoding in ["utf-8", "gbk"]:
        try:
            return TextLoader(file_path, encoding=encoding).load()
        except Exception:
            continue
    return []


def docx_loader_sync(file_path: str) -> list[Document]:
    try:
        return Docx2txtLoader(file_path).load()
    except Exception as e:
        logger.error(f"DOCX加载失败: {file_path} -> {e}")
        return []


def md_loader_sync(file_path: str) -> list[Document]:
    try:
        return UnstructuredMarkdownLoader(file_path, mode="single").load()
    except Exception as e:
        logger.error(f"MD加载失败: {file_path} -> {e}")
        return []


def pptx_loader_sync(file_path: str) -> list[Document]:
    try:
        return UnstructuredPowerPointLoader(file_path, mode="single").load()
    except Exception as e:
        logger.error(f"PPTX加载失败: {file_path} -> {e}")
        return []


def load_file_sync(file_path: str) -> list[Document]:
    """根据扩展名路由到对应同步加载器"""
    ext = os.path.splitext(file_path)[1].lower()
    loader_map = {
        ".pdf": pdf_loader_sync,
        ".txt": txt_loader_sync,
        ".docx": docx_loader_sync,
        ".md": md_loader_sync,
        ".pptx": pptx_loader_sync,
    }
    loader = loader_map.get(ext)
    if loader:
        return loader(file_path)
    return []


# ==================== 时间元数据提取 ====================
def get_file_mtime_sync(file_path: str) -> str:
    """获取文件的最后修改时间（ISO格式），用于文档时间标签"""
    try:
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except Exception:
        return ""


def extract_content_time_range(text: str) -> str:
    """从文档内容中提取年份范围（如 '2005-2025'）。

    匹配中文年份格式：2005年、2023年度、2018-2020年
    返回格式："2005-2025" 或 "2005" 或 ""（无法提取时）
    """
    years = re.findall(r'(19\d{2}|20\d{2})\s*年', text)
    if not years:
        return ""
    years_int = sorted(set(int(y) for y in years))
    if len(years_int) == 1:
        return str(years_int[0])
    return f"{years_int[0]}-{years_int[-1]}"
