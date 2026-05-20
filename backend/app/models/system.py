# ruff: noqa: F821,E402
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class AuditTrail(Base, TimestampMixin):
    """审计日志"""
    __tablename__ = "audit_trail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # CREATE, UPDATE, DELETE
    old_values: Mapped[Optional[str]] = mapped_column(Text)
    new_values: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)



class Notification(Base, TimestampMixin):
    """通知中心（小铃铛）"""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    related_type: Mapped[Optional[str]] = mapped_column(String(50))
    related_id: Mapped[Optional[int]] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


# ==================== 系统配置 ====================


class SystemConfig(Base, TimestampMixin):
    """系统配置"""
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    config_type: Mapped[str] = mapped_column(String(20), default="string")  # string, int, float, bool, json
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True)

"""
成品销售模块V2 - 模型导出扩展
在现有 models/__init__.py 中追加导入以下内容
"""

# ==================== 新增导入（追加到现有 __init__.py 末尾）====================

from app.models.finished_product_v2 import (  # noqa: E402
    # 枚举
    SlaughterType as SlaughterType,
    LossType as LossType,
    SaleItemType as SaleItemType,
    # 模型
    DailySlaughterRecord as DailySlaughterRecord,
    WarehousePurchaseOrder as WarehousePurchaseOrder,
    WarehouseStock as WarehouseStock,
    FinishedProductSaleItem as FinishedProductSaleItem,
    LossRecord as LossRecord,
    FinishedProductCommission as FinishedProductCommission,
    SlaughterFinishedProduct as SlaughterFinishedProduct,
    MaterialTraceability as MaterialTraceability,
)

from app.models.finished_products import (  # noqa: E402
    ProductTemplate as ProductTemplate,
    TemplatePart as TemplatePart,
    TemplateBOM as TemplateBOM,
    TemplatePackaging as TemplatePackaging,
    ProductVariant as ProductVariant,
    VariantPackaging as VariantPackaging,
    VariantAccessory as VariantAccessory,
)

from app.models.material_supplier import MaterialSupplier as MaterialSupplier  # noqa: E402

from app.models.returns import (
    ReturnReason as ReturnReason,
    ReturnStatus as ReturnStatus,
    RefundMethod as RefundMethod,
    ReturnAttachmentType as ReturnAttachmentType,
    ReturnOrder as ReturnOrder,
    ReturnItem as ReturnItem,
    ReturnAttachment as ReturnAttachment,
)

# 这样现有代码可以通过 from app.models import ProductTemplate 等方式使用新模型



# ==================== 国内采购与成品销售模块 (迁移自 salmon-finance-v4) ====================

