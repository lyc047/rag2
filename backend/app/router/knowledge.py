"""知识库路由 —— 文件上传、列表、删除、切片查看"""
import os
import tempfile
import asyncio
import json
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.core.response import success_response
from app.rag.vector_store import vector_store_service
from app.rag.loader import get_file_md5_sync, load_file_sync
from app.config.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from app.core.logger import logger

router = APIRouter()


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(..., description="要上传的文件列表")):
    """批量上传文件到知识库 —— SSE流式返回处理进度"""

    async def event_stream():
        results = {"success": 0, "failed": 0}
        for file in files:
            filename = file.filename
            ext = os.path.splitext(filename)[1].lower()

            # 文件类型校验
            if ext not in ALLOWED_EXTENSIONS:
                yield f"data: {json.dumps({'event_type': 'error', 'filename': filename, 'message': f'不支持的文件类型: {ext}，仅支持PDF/TXT/DOCX/MD/PPTX'}, ensure_ascii=False)}\n\n"
                results["failed"] += 1
                continue

            # 文件大小校验
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                yield f"data: {json.dumps({'event_type': 'error', 'filename': filename, 'message': '文件超过20MB限制'}, ensure_ascii=False)}\n\n"
                results["failed"] += 1
                continue

            # 写入临时文件
            yield f"data: {json.dumps({'event_type': 'start', 'filename': filename, 'message': f'开始处理 {filename}'}, ensure_ascii=False)}\n\n"

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                # 处理文档
                result = await vector_store_service.add_document(tmp_path, filename)
                if result.get("success"):
                    yield f"data: {json.dumps({'event_type': 'completed', 'filename': filename, 'message': f'{filename} 处理完成'}, ensure_ascii=False)}\n\n"
                    results["success"] += 1
                elif result.get("skipped"):
                    yield f"data: {json.dumps({'event_type': 'skipped', 'filename': filename, 'message': f'{filename} 已存在，跳过'}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'event_type': 'error', 'filename': filename, 'message': result.get('error', '处理失败')}, ensure_ascii=False)}\n\n"
                    results["failed"] += 1
            except Exception as e:
                yield f"data: {json.dumps({'event_type': 'error', 'filename': filename, 'message': str(e)}, ensure_ascii=False)}\n\n"
                results["failed"] += 1
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        yield f"data: {json.dumps({'event_type': 'finish', 'success_count': results['success'], 'failed_count': results['failed']}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/documents")
async def list_documents():
    """获取所有已入库文档列表"""
    records = await vector_store_service.list_documents()
    return success_response(data=records)


@router.get("/documents/{md5_hex}/chunks")
async def get_document_chunks(md5_hex: str):
    """获取指定文档的所有切片"""
    chunks = await vector_store_service.get_document_chunks(md5_hex)
    return success_response(data={"md5": md5_hex, "chunks": chunks})


@router.delete("/documents/{md5_hex}")
async def delete_document(md5_hex: str):
    """删除指定文档"""
    await vector_store_service.delete_document(md5_hex)
    return success_response(message=f"文档 {md5_hex[:16]}... 已删除")


@router.delete("/clear")
async def clear_knowledge():
    """清空知识库"""
    await vector_store_service.clear_knowledge()
    return success_response(message="知识库已清空")
