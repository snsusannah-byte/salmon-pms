from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """用户管理"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)

    # 关联设置
    settings: Mapped[Optional["UserSettings"]] = relationship("UserSettings", uselist=False, back_populates="user")



class UserSettings(Base, TimestampMixin):
    """用户个性化设置"""
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    # 通知设置
    notify_customs_change: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_batch_lock: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_payment: Mapped[bool] = mapped_column(Boolean, default=False)

    # 界面设置
    compact_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_refresh: Mapped[bool] = mapped_column(Boolean, default=True)

    # 关联
    user: Mapped["User"] = relationship("User", back_populates="settings")


# ==================== 采购层 ====================

