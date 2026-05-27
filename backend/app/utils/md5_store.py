"""MD5去重存储 —— 基于文本文件记录已处理文档的MD5值"""
import json
import os
import aiofiles
from app.core.logger import logger


class MD5Store:
    """MD5记录管理器，每个文件一行JSON"""

    def __init__(self, store_dir: str = "data/md5_store"):
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)
        self._store_file = os.path.join(store_dir, "md5_records.jsonl")

    async def exists(self, md5_hex: str) -> bool:
        """检查MD5是否已存在"""
        if not os.path.exists(self._store_file):
            return False
        async with aiofiles.open(self._store_file, "r", encoding="utf-8") as f:
            async for line in f:
                try:
                    record = json.loads(line.strip())
                    if record.get("md5") == md5_hex:
                        return True
                except json.JSONDecodeError:
                    continue
        return False

    async def save(self, md5_hex: str, filename: str):
        """保存MD5记录"""
        record = {"md5": md5_hex, "filename": filename}
        async with aiofiles.open(self._store_file, "a", encoding="utf-8") as f:
            await f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info(f"MD5已保存: {filename} -> {md5_hex[:16]}...")

    async def list_all(self) -> list:
        """列出所有记录"""
        records = []
        if not os.path.exists(self._store_file):
            return records
        async with aiofiles.open(self._store_file, "r", encoding="utf-8") as f:
            async for line in f:
                try:
                    records.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return records

    async def delete(self, md5_hex: str):
        """删除指定MD5记录"""
        if not os.path.exists(self._store_file):
            return
        records = []
        async with aiofiles.open(self._store_file, "r", encoding="utf-8") as f:
            async for line in f:
                try:
                    r = json.loads(line.strip())
                    if r.get("md5") != md5_hex:
                        records.append(r)
                except json.JSONDecodeError:
                    continue
        async with aiofiles.open(self._store_file, "w", encoding="utf-8") as f:
            for r in records:
                await f.write(json.dumps(r, ensure_ascii=False) + "\n")

    async def clear(self):
        """清空所有记录"""
        if os.path.exists(self._store_file):
            os.remove(self._store_file)
