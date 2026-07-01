# ruff: noqa: F821,E402
from datetime import datetime

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
    old_values: Mapped[str | None] = mapped_column(Text)
    new_values: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(Text)



class Notification(Base, TimestampMixin):
    """通知中心（小铃铛）"""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    related_type: Mapped[str | None] = mapped_column(String(50))
    related_id: Mapped[int | None] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)


# ==================== 系统配置 ====================


class SystemConfig(Base, TimestampMixin):
    """系统配置"""
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    config_type: Mapped[str] = mapped_column(String(20), default="string")  # string, int, float, bool, json
    description: Mapped[str | None] = mapped_column(Text)
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True)

"""
成品销售模块V2 - 模型导出扩展
在现有 models/__init__.py 中追加导入以下内容
"""

# ==================== 新增导入（追加到现有 __init__.py 末尾）====================

from app.models.finished_product_v2 import (
    # 模型
    DailySlaughterRecord as DailySlaughterRecord,
)
from app.models.finished_product_v2 import (
    FinishedProductCommission as FinishedProductCommission,
)
from app.models.finished_product_v2 import (
    FinishedProductSaleItem as FinishedProductSaleItem,
)
from app.models.finished_product_v2 import (
    LossRecord as LossRecord,
)
from app.models.finished_product_v2 import (
    LossType as LossType,
)
from app.models.finished_product_v2 import (
    MaterialTraceability as MaterialTraceability,
)
from app.models.finished_product_v2 import (
    SaleItemType as SaleItemType,
)
from app.models.finished_product_v2 import (
    SlaughterFinishedProduct as SlaughterFinishedProduct,
)
from app.models.finished_product_v2 import (  # noqa: E402
    # 枚举
    SlaughterType as SlaughterType,
)
from app.models.finished_product_v2 import (
    WarehousePurchaseOrder as WarehousePurchaseOrder,
)
from app.models.finished_product_v2 import (
    WarehouseStock as WarehouseStock,
)
from app.models.finished_products import (  # noqa: E402
    ProductTemplate as ProductTemplate,
)
from app.models.finished_products import (
    ProductVariant as ProductVariant,
)
from app.models.finished_products import (
    TemplateBOM as TemplateBOM,
)
from app.models.finished_products import (
    TemplatePackaging as TemplatePackaging,
)
from app.models.finished_products import (
    TemplatePart as TemplatePart,
)
from app.models.finished_products import (
    VariantAccessory as VariantAccessory,
)
from app.models.finished_products import (
    VariantPackaging as VariantPackaging,
)
from app.models.material_supplier import (
    MaterialSupplier as MaterialSupplier,  # noqa: E402
)
from app.models.returns import (
    RefundMethod as RefundMethod,
)
from app.models.returns import (
    ReturnAttachment as ReturnAttachment,
)
from app.models.returns import (
    ReturnAttachmentType as ReturnAttachmentType,
)
from app.models.returns import (
    ReturnItem as ReturnItem,
)
from app.models.returns import (
    ReturnOrder as ReturnOrder,
)
from app.models.returns import (
    ReturnReason as ReturnReason,
)
from app.models.returns import (
    ReturnStatus as ReturnStatus,
)

# 这样现有代码可以通过 from app.models import ProductTemplate 等方式使用新模型



# ==================== 国内采购与成品销售模块 (迁移自 salmon-finance-v4) ====================

