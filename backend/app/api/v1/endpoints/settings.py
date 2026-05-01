from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()

@router.get("/configs")
async def list_system_configs():
    """系统配置列表"""
    return {"message": "系统配置列表 - 待实现"}

@router.put("/configs/{config_key}")
async def update_system_config(config_key: str):
    """更新系统配置"""
    return {"message": f"更新系统配置 - 待实现, key={config_key}"}

@router.get("/users")
async def list_users():
    """用户列表"""
    return {"message": "用户列表 - 待实现"}

@router.post("/users")
async def create_user():
    """创建用户"""
    return {"message": "创建用户 - 待实现"}

@router.get("/audit-trail")
async def list_audit_trail():
    """审计日志"""
    return {"message": "审计日志 - 待实现"}
