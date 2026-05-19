import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine
from app.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - 只创建表，不删除数据
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Salmon PMS API",
    description="三文鱼项目管理系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from app.api.v1 import api_router  # noqa: E402
app.include_router(api_router, prefix="/api/v1")

# V4 迁移路由单独挂载
from app.api.v1.endpoints import finance_v4_migration  # noqa: E402
app.include_router(finance_v4_migration.router, prefix="/api/v4")

# Static files for uploads
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Health check
@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
