import json
import logging
import os
import traceback
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine
from app.models.base import Base

# 错误日志配置
logger = logging.getLogger("salmon.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 生产环境安全检查 ──
    try:
        settings.validate_production()
    except RuntimeError as e:
        logger.critical(f"启动失败: {e}")
        raise

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
from app.api.v1.endpoints import material_categories, materials, warehouse  # noqa: E402

app.include_router(materials.router, prefix="/api/v4/materials", tags=["物料管理"])
app.include_router(material_categories.router, prefix="/api/v4/material-categories", tags=["物料分类"])
app.include_router(warehouse.router, prefix="/api/v4/warehouse", tags=["仓库管理"])

# 注册 V1 API routers
from app.api.v1.endpoints import client_errors  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
app.include_router(client_errors.router, prefix="/api/v1")

# V4 迁移路由单独挂载
from app.api.v1.endpoints import finance_v4_migration  # noqa: E402

app.include_router(finance_v4_migration.router, prefix="/api/v4")

# Static files for uploads
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# 全局异常捕获 - 500 错误自动落盘


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理异常，记录到 client_errors.jsonl"""
    try:
        err_path = os.path.join(settings.LOG_DIR, "client_errors.jsonl")
        with open(err_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "server_500",
                "message": str(exc)[:500],
                "stack": traceback.format_exc()[:2000],
                "url": str(request.url),
                "api_path": request.url.path,
                "method": request.method,
                "timestamp": datetime.utcnow().isoformat(),
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 日志写入失败不阻塞主流程

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "path": str(request.url)},
    )

# Health check
@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
