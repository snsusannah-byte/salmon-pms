# ruff: noqa: F403, F405
# models/__init__.py - 统一导出所有模型（按模块拆分为子文件）

# 核心模型（拆分后的子模块）
from app.models.enums import *  # noqa: F401
from app.models.company import *  # noqa: F401
from app.models.user import *  # noqa: F401
from app.models.product import *  # noqa: F401
from app.models.invoice import *  # noqa: F401
from app.models.batch import *  # noqa: F401
from app.models.sales import *  # noqa: F401
from app.models.finished_product import *  # noqa: F401
from app.models.finance import *  # noqa: F401
from app.models.warehouse import *  # noqa: F401
from app.models.system import *  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401

# 已有独立文件的其他模型（显式 re-export）
from app.models.finished_products import (
    ProductTemplate as ProductTemplate,
    TemplatePart as TemplatePart,
    TemplateBOM as TemplateBOM,
    TemplatePackaging as TemplatePackaging,
    ProductVariant as ProductVariant,
    VariantPackaging as VariantPackaging,
    VariantAccessory as VariantAccessory,
    # 新增：重构后的系列/规格/价格层级
    ProductSeries as ProductSeries,
    ProductSpec as ProductSpec,
    VariantPriceTier as VariantPriceTier,
)
from app.models.material_supplier import MaterialSupplier as MaterialSupplier
from app.models.material_purchase import (
    MaterialPurchaseOrder as MaterialPurchaseOrder,
    MaterialPurchaseItem as MaterialPurchaseItem,
    MaterialBatch as MaterialBatch,
)
from app.models.returns import (
    ReturnReason as ReturnReason,
    ReturnStatus as ReturnStatus,
    RefundMethod as RefundMethod,
    ReturnAttachmentType as ReturnAttachmentType,
    ReturnOrder as ReturnOrder,
    ReturnItem as ReturnItem,
    ReturnAttachment as ReturnAttachment,
)
