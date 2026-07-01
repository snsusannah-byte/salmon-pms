"""
采购入库单查询 API (基于 PurchaseOrderV2)

本模块提供采购入库单的只读查询和删除接口。
主要服务于需要按 PurchaseOrderV2 模型查询的场景。
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_warehouse, require_admin
from app.models.finance import PurchaseOrderV2, PurchaseOrderProductV2
from app.models import Company

router = APIRouter()


@router.get("/import-inbound")
async def list_purchase_inbounds(
    order_type: str | None = Query(None, description="raw_material=整鱼, accessories=辅料"),
    status: str | None = Query(None),
    supplier_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """采购入库单列表（基于 PurchaseOrderV2）"""
    query = select(PurchaseOrderV2, Company).join(
        Company, PurchaseOrderV2.supplier_id == Company.id, isouter=True
    )

    if order_type:
        query = query.where(PurchaseOrderV2.order_type == order_type)
    if status:
        query = query.where(PurchaseOrderV2.status == status)
    if supplier_id:
        query = query.where(PurchaseOrderV2.supplier_id == supplier_id)

    query = query.order_by(desc(PurchaseOrderV2.purchase_date), desc(PurchaseOrderV2.id))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    result = await db.execute(query.offset(skip).limit(limit))
    rows = result.all()

    items = []
    for po, supplier in rows:
        # 查询明细汇总
        products_result = await db.execute(
            select(PurchaseOrderProductV2).where(
                PurchaseOrderProductV2.purchase_order_id == po.id
            )
        )
        products = list(products_result.scalars().all())

        items.append({
            "id": po.id,
            "purchase_no": po.purchase_no,
            "purchase_date": po.purchase_date,
            "supplier_id": po.supplier_id,
            "supplier_name": supplier.name if supplier else po.supplier_name or "",
            "total_amount": po.total_amount,
            "after_sales_adjustment": po.after_sales_adjustment or Decimal("0"),
            "net_amount": po.total_amount - (po.after_sales_adjustment or Decimal("0")),
            "total_weight": po.total_weight,
            "total_boxes": po.total_boxes,
            "order_type": po.order_type,
            "status": po.status,
            "remark": po.remark,
            "product_count": len(products),
            "created_at": po.created_at.isoformat() if po.created_at else None,
        })

    return {"total": total, "items": items, "skip": skip, "limit": limit}


@router.get("/import-inbound/{inbound_id}")
async def get_purchase_inbound(
    inbound_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """采购入库单详情"""
    result = await db.execute(
        select(PurchaseOrderV2).where(PurchaseOrderV2.id == inbound_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="采购入库单不存在")

    # 查询明细
    products_result = await db.execute(
        select(PurchaseOrderProductV2).where(
            PurchaseOrderProductV2.purchase_order_id == po.id
        )
    )
    products = list(products_result.scalars().all())

    supplier_result = await db.execute(
        select(Company).where(Company.id == po.supplier_id)
    )
    supplier = supplier_result.scalar_one_or_none()

    return {
        "id": po.id,
        "purchase_no": po.purchase_no,
        "purchase_date": po.purchase_date,
        "supplier_id": po.supplier_id,
        "supplier_name": supplier.name if supplier else po.supplier_name or "",
        "total_amount": po.total_amount,
        "after_sales_adjustment": po.after_sales_adjustment or Decimal("0"),
        "net_amount": po.total_amount - (po.after_sales_adjustment or Decimal("0")),
        "total_weight": po.total_weight,
        "total_boxes": po.total_boxes,
        "order_type": po.order_type,
        "status": po.status,
        "remark": po.remark,
        "sale_id": po.sale_id,
        "products": [
            {
                "id": p.id,
                "product_name": p.product_name,
                "product_spec": p.product_spec,
                "box_count": p.box_count,
                "weight_kg": p.weight_kg,
                "unit": p.unit,
                "unit_price": p.unit_price,
                "total_amount": p.total_amount,
            }
            for p in products
        ],
        "created_at": po.created_at.isoformat() if po.created_at else None,
    }


@router.delete("/import-inbound/{inbound_id}", status_code=204)
async def delete_purchase_inbound(
    inbound_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    """删除采购入库单（仅删除 PurchaseOrderV2 记录，不级联删除 MaterialPurchaseOrder）"""
    from sqlalchemy import delete

    result = await db.execute(
        select(PurchaseOrderV2).where(PurchaseOrderV2.id == inbound_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="采购入库单不存在")

    # 删除明细
    await db.execute(
        delete(PurchaseOrderProductV2).where(
            PurchaseOrderProductV2.purchase_order_id == po.id
        )
    )
    # 删除主表
    await db.delete(po)
    await db.commit()


# ==================== 售后扣款 ====================

@router.post("/import-inbound/{inbound_id}/after-sales-adjustment")
async def purchase_inbound_after_sales_adjustment(
    inbound_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """采购入库单售后扣款 — 调整应付金额"""
    result = await db.execute(
        select(PurchaseOrderV2).where(PurchaseOrderV2.id == inbound_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="采购入库单不存在")

    adjustment = Decimal(str(data.get("after_sales_adjustment", 0)))
    if adjustment < 0:
        raise HTTPException(status_code=400, detail="售后扣款金额不能为负数")
    if adjustment > po.total_amount:
        raise HTTPException(status_code=400, detail="售后扣款金额不能超过采购总金额")

    po.after_sales_adjustment = adjustment

    await db.commit()
    await db.refresh(po)

    net_amount = po.total_amount - adjustment
    return {
        "id": po.id,
        "after_sales_adjustment": float(po.after_sales_adjustment),
        "net_amount": float(net_amount),
        "message": "售后扣款调整成功",
    }
