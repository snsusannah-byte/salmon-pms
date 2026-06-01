"""
用户角色与权限体系

角色设计（4级）:
- admin: 管理员 — 全部权限
- finance: 财务 — 财务报表、银行流水、应收应付
- sales: 销售 — 销售单、客户管理、收款
- warehouse: 仓库 — 入库出库、库存、物料
- user: 普通用户 — 只读查看（默认）
"""
from enum import Enum as PyEnum
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models import User


class UserRole(str, PyEnum):
    """用户角色枚举"""
    ADMIN = "admin"           # 管理员
    FINANCE = "finance"       # 财务
    SALES = "sales"           # 销售
    WAREHOUSE = "warehouse"   # 仓库
    USER = "user"             # 普通用户（默认）


# ========== 权限矩阵 ==========

# 模块 -> 允许的角色集合
MODULE_PERMISSIONS = {
    # 财务模块（三大报表、银行流水、应收应付）
    "finance": {UserRole.ADMIN, UserRole.FINANCE},
    "reports": {UserRole.ADMIN, UserRole.FINANCE},

    # 销售模块（销售单、客户、收款）
    "sales": {UserRole.ADMIN, UserRole.SALES},
    "customers": {UserRole.ADMIN, UserRole.SALES},
    "receivable": {UserRole.ADMIN, UserRole.SALES, UserRole.FINANCE},

    # 仓库模块（入库出库、库存、物料、批次）
    "warehouse": {UserRole.ADMIN, UserRole.WAREHOUSE},
    "materials": {UserRole.ADMIN, UserRole.WAREHOUSE},
    "batches": {UserRole.ADMIN, UserRole.WAREHOUSE, UserRole.SALES},

    # 采购模块（进口单证、供应商）
    "purchase": {UserRole.ADMIN, UserRole.WAREHOUSE, UserRole.SALES},
    "suppliers": {UserRole.ADMIN, UserRole.WAREHOUSE, UserRole.SALES},

    # 生产模块（宰杀日报、成品定义）
    "production": {UserRole.ADMIN, UserRole.WAREHOUSE},

    # 系统管理（用户、设置）— 仅管理员
    "system": {UserRole.ADMIN},
    "users": {UserRole.ADMIN},
}

# 敏感操作 -> 需要的角色
SENSITIVE_OPERATIONS = {
    "delete": {UserRole.ADMIN},
    "lock": {UserRole.ADMIN, UserRole.WAREHOUSE, UserRole.FINANCE},
    "unlock": {UserRole.ADMIN},
    "batch_import": {UserRole.ADMIN, UserRole.FINANCE},
    "approve": {UserRole.ADMIN, UserRole.FINANCE},
}


def require_role(*roles: UserRole):
    """
    角色权限校验依赖工厂

    用法:
        @router.post("/items")
        async def create_item(
            user: User = Depends(require_role(UserRole.ADMIN, UserRole.SALES))
        ):
            ...
    """
    allowed = set(roles)

    async def role_checker(
        user: User = Depends(get_current_user),
    ) -> User:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用",
            )
        user_role = UserRole(user.role) if user.role in {r.value for r in UserRole} else UserRole.USER
        if user_role not in allowed and user_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要 {', '.join(r.value for r in roles)} 角色",
            )
        return user

    return role_checker


# ========== 常用快捷依赖 ==========

require_admin = require_role(UserRole.ADMIN)
require_finance = require_role(UserRole.ADMIN, UserRole.FINANCE)
require_sales = require_role(UserRole.ADMIN, UserRole.SALES)
require_warehouse = require_role(UserRole.ADMIN, UserRole.WAREHOUSE)
require_finance_or_sales = require_role(UserRole.ADMIN, UserRole.FINANCE, UserRole.SALES)


# ========== 操作日志记录器 ==========

async def log_operation(
    db: AsyncSession,
    user_id: int,
    action: str,
    module: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[str] = None,
    old_values: Optional[str] = None,
    new_values: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    记录敏感操作到审计日志表
    """
    try:
        from app.models.audit import AuditLog
        log = AuditLog(
            user_id=user_id,
            action=action,
            module=module,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        await db.commit()
    except Exception:
        # 日志记录失败不应阻塞主流程
        import logging
        logger = logging.getLogger("salmon.audit")
        logger.warning(f"AUDIT_LOG_FAIL user={user_id} action={action} module={module}", exc_info=True)
        # 回滚避免影响主事务
        try:
            await db.rollback()
        except Exception:
            pass
