import os
import secrets
from typing import List

from pydantic_settings import BaseSettings


def _generate_secret() -> str:
    """生成安全的随机密钥（开发环境 fallback）"""
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    APP_NAME: str = "Salmon PMS"
    DEBUG: bool = True

    # ── Database ──
    # 优先从环境变量读取，生产环境必须配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://salmon:salmon123@localhost:5432/salmon_pms",
    )

    # ── Redis ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── MinIO ──
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "salmon")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "salmon12345")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "salmon-pms")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # ── Security ──
    # 生产环境必须设置强密钥；开发环境自动生成
    SECRET_KEY: str = os.getenv("SALMON_SECRET_KEY", _generate_secret())
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # ── CORS ──
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]
    # 允许从环境变量追加 CORS（逗号分隔）
    _extra_cors: str = os.getenv("CORS_ORIGINS", "")

    # ── 部署模式 ──
    ENV: str = os.getenv("SALMON_ENV", "development")  # development | production | testing

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENV.lower() == "testing"

    def validate_production(self) -> None:
        """生产环境安全检查 — 启动时调用"""
        if not self.is_production:
            return
        issues: List[str] = []
        if self.DEBUG:
            issues.append("DEBUG=True 不应出现在生产环境")
        if self.SECRET_KEY == _generate_secret() or len(self.SECRET_KEY) < 32:
            issues.append("SECRET_KEY 未正确配置或为弱密钥")
        if "salmon123" in self.DATABASE_URL:
            issues.append("DATABASE_URL 使用了默认密码")
        if "salmon12345" in self.MINIO_SECRET_KEY:
            issues.append("MINIO_SECRET_KEY 使用了默认值")
        if issues:
            raise RuntimeError(
                "生产环境配置错误:\n" + "\n".join(f"  - {i}" for i in issues)
            )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

