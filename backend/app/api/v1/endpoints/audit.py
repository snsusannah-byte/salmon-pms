from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_admin
from app.models import AuditLog, User

router = APIRouter()


@router.get("/logs", response_model=dict)
async def list_audit_logs(
    module: str | None = Query(None, description="模块过滤"),
    action: str | None = Query(None, description="操作类型过滤"),
    user_id: int | None = Query(None, description="用户ID过滤"),
    start_date: datetime | None = Query(None, description="开始日期"),
    end_date: datetime | None = Query(None, description="结束日期"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """查询审计日志 — 仅限管理员"""
    query = select(AuditLog)
    
    if module:
        query = query.where(AuditLog.module == module)
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if start_date and end_date:
        query = query.where(and_(AuditLog.created_at >= start_date, AuditLog.created_at <= end_date))
    elif start_date:
        query = query.where(AuditLog.created_at >= start_date)
    elif end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    # 总数
    count_result = await db.execute(select(AuditLog).where(
        *(cond for cond in [
            AuditLog.module == module if module else None,
            AuditLog.action == action if action else None,
            AuditLog.user_id == user_id if user_id else None,
            and_(AuditLog.created_at >= start_date, AuditLog.created_at <= end_date) if start_date and end_date else None,
            AuditLog.created_at >= start_date if start_date and not end_date else None,
            AuditLog.created_at <= end_date if end_date and not start_date else None,
        ] if cond is not None)
    ))
    total = len(count_result.scalars().all())
    
    # 分页查询
    query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "module": log.module,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.get("/logs/modules", response_model=dict)
async def get_audit_modules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """获取所有审计模块列表"""
    result = await db.execute(select(AuditLog.module).distinct())
    modules = [m for m in result.scalars().all() if m]
    return {"modules": modules}
