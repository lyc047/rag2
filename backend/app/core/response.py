"""统一响应格式"""
import json
from datetime import datetime, date
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(data=None, message="success"):
    """成功响应 —— 使用jsonable_encoder确保datetime等类型可序列化"""
    return JSONResponse(content=jsonable_encoder({"code": 200, "message": message, "data": data}))


def error_response(code=500, message="error", detail=None):
    """错误响应"""
    return JSONResponse(
        status_code=code if 400 <= code < 600 else 500,
        content=jsonable_encoder({"code": code, "message": message, "detail": detail})
    )
