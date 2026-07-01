# ruff: noqa: F403, F405
# models/__init__.py - 统一导出所有模型（按模块拆分为子文件）

# 核心模型（拆分后的子模块）
from app.models.audit import AuditLog  # noqa: F401
from app.models.batch import *  # noqa: F401
from app.models.company import *  # noqa: F401
from app.models.enums import *  # noqa: F401
from app.models.finance import *  # noqa: F401
from app.models.finished_product import *  # noqa: F401
from app.models.finished_products import (
    # 新增：重构后的系列/规格/价格层级
    ProductSeries as ProductSeries,
)
from app.models.finished_products import (
    ProductSpec as ProductSpec,
)

# 已有独立文件的其他模型（显式 re-export）
from app.models.finished_products import (
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
from app.models.finished_products import (
    VariantPriceTier as VariantPriceTier,
)
from app.models.invoice import *  # noqa: F401
from app.models.material_purchase import (
    MaterialBatch as MaterialBatch,
)
from app.models.material_purchase import (
    MaterialPurchaseItem as MaterialPurchaseItem,
)
from app.models.material_purchase import (
    MaterialPurchaseOrder as MaterialPurchaseOrder,
)
from app.models.material_supplier import MaterialSupplier as MaterialSupplier
from app.models.product import *  # noqa: F401
from app.models.purchase_returns import (
    PurchaseRefundMethod as PurchaseRefundMethod,
)
from app.models.purchase_returns import (
    PurchaseReturnAttachment as PurchaseReturnAttachment,
)
from app.models.purchase_returns import (
    PurchaseReturnAttachmentType as PurchaseReturnAttachmentType,
)
from app.models.purchase_returns import (
    PurchaseReturnItem as PurchaseReturnItem,
)
from app.models.purchase_returns import (
    PurchaseReturnOrder as PurchaseReturnOrder,
)
from app.models.purchase_returns import (
    PurchaseReturnStatus as PurchaseReturnStatus,
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
from app.models.sales import *  # noqa: F401
from app.models.system import *  # noqa: F401
from app.models.user import *  # noqa: F401
from app.models.warehouse import *  # noqa: F401
