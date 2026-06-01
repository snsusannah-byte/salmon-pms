"""
操作审计日志模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """操作审计日志 — 记录敏感操作"""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 操作人
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 操作信息
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    """操作类型: create | update | delete | lock | unlock | approve | import | export"""

    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    """所属模块: companies | finance | warehouse | sales | batches | system | auth"""

    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """资源类型: Company | BankAccount | Transaction | Batch | ..."""

    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    """资源主键"""

    # 详情
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """JSON 或文本形式的变更详情"""

    old_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """变更前的值（JSON）"""

    new_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """变更后的值（JSON）"""

    # 网络信息
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    """IPv4 或 IPv6"""

    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """浏览器 User-Agent"""

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_logs_user_module", "user_id", "module"),
        Index("ix_audit_logs_module_action", "module", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        {"comment": "操作审计日志表 — 记录所有敏感操作"},
    )
