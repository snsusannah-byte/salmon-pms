"""
文件存储服务 — 支持本地磁盘和 MinIO

使用方式:
    from app.services.storage_service import StorageService
    
    # 上传文件
    url = await StorageService.upload_file(file_content, "returns/202501/file.jpg")
    
    # 下载文件
    content = await StorageService.download_file("returns/202501/file.jpg")
    
    # 删除文件
    await StorageService.delete_file("returns/202501/file.jpg")
"""
import io
import os
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings

# 尝试导入 MinIO
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False


class StorageService:
    """文件存储服务 — 统一封装本地存储和 MinIO"""

    _minio_client: "Minio | None" = None
    _use_minio: bool = False

    @classmethod
    def _get_minio_client(cls) -> "Minio | None":
        """获取 MinIO 客户端（懒加载）"""
        if not MINIO_AVAILABLE:
            return None
        if cls._minio_client is None:
            try:
                cls._minio_client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE,
                )
                # 验证连接
                cls._minio_client.list_buckets()
                cls._use_minio = True
            except Exception:
                cls._minio_client = None
                cls._use_minio = False
        return cls._minio_client

    @classmethod
    def _ensure_bucket(cls):
        """确保存储桶存在"""
        client = cls._get_minio_client()
        if client and not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)

    @classmethod
    async def upload_file(
        cls,
        file_content: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        上传文件
        
        Returns:
            文件访问 URL 或路径
        """
        client = cls._get_minio_client()
        
        if client and cls._use_minio:
            # 使用 MinIO
            cls._ensure_bucket()
            try:
                client.put_object(
                    settings.MINIO_BUCKET,
                    object_name,
                    io.BytesIO(file_content),
                    length=len(file_content),
                    content_type=content_type,
                )
                # 返回访问 URL
                return f"/uploads/{object_name}"
            except Exception:
                # MinIO 失败，回退到本地存储
                pass
        
        # 本地存储（回退）
        return await cls._upload_local(file_content, object_name)

    @classmethod
    async def _upload_local(cls, file_content: bytes, object_name: str) -> str:
        """本地文件存储"""
        upload_dir = Path(os.path.dirname(__file__)).parent.parent / "uploads"
        file_path = upload_dir / object_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return f"/uploads/{object_name}"

    @classmethod
    async def download_file(cls, object_name: str) -> bytes:
        """下载文件"""
        client = cls._get_minio_client()
        
        if client and cls._use_minio:
            try:
                response = client.get_object(settings.MINIO_BUCKET, object_name)
                return response.read()
            except Exception:
                pass
        
        # 本地存储回退
        upload_dir = Path(os.path.dirname(__file__)).parent.parent / "uploads"
        file_path = upload_dir / object_name
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {object_name}")
        
        with open(file_path, "rb") as f:
            return f.read()

    @classmethod
    async def delete_file(cls, object_name: str) -> bool:
        """删除文件"""
        client = cls._get_minio_client()
        deleted = False
        
        # 尝试从 MinIO 删除
        if client and cls._use_minio:
            try:
                client.remove_object(settings.MINIO_BUCKET, object_name)
                deleted = True
            except Exception:
                pass
        
        # 尝试从本地删除
        upload_dir = Path(os.path.dirname(__file__)).parent.parent / "uploads"
        file_path = upload_dir / object_name
        if file_path.exists():
            file_path.unlink()
            deleted = True
        
        return deleted

    @classmethod
    def get_file_url(cls, object_name: str) -> str:
        """获取文件访问 URL"""
        return f"/uploads/{object_name}"
