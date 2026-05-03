from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Salmon PMS"
    DEBUG: bool = True
    
    # Database
    # SQLite (开发环境保留)
    # DATABASE_URL: str = "sqlite+aiosqlite:///./salmon_pms_dev.db"
    # PostgreSQL (生产环境)
    DATABASE_URL: str = "postgresql+asyncpg://salmon:salmon123@localhost:5432/salmon_pms"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "salmon"
    MINIO_SECRET_KEY: str = "salmon12345"
    MINIO_BUCKET: str = "salmon-pms"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://192.168.201.144:5173",
        "http://127.0.0.1:5173",
    ]
    
    class Config:
        env_file = ".env"


settings = Settings()
