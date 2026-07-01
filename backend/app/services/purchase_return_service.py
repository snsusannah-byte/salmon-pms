"""采购售后服务层 — 三文鱼PMS

参考销售退货单（ReturnService），但方向相反：
- 销售退货：退钱给客户
- 采购售后：抵扣应付款 / 供应商退钱

**业务流程（简化版）：**
- 创建售后单 → 立即扣款（after_sales_adjustment）
- 编辑售后单 → 回滚旧扣款，应用新扣款
- 删除售后单 → 回滚扣款，删除记录
- 无审批流程
"""
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Company,
    PurchaseOrderProductV2,
    PurchaseOrderV2,
    PurchaseReturnAttachment,
    PurchaseReturnItem,
    PurchaseReturnOrder,
    PurchaseReturnStatus,
    MaterialPurchaseOrder,
    MaterialPurchaseItem,
)


class PurchaseReturnService:
    """采购售后服务"""

    # ==================== 编号生成 ====================

    @staticmethod
    async def _generate_return_no(db: AsyncSession) -> str:
        today = date.today()
        prefix = f"SH{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.count()).select_from(
                select(PurchaseReturnOrder).where(PurchaseReturnOrder.return_no.like(f"{prefix}-%")).subquery()
            )
        )
        count = result.scalar() or 0
        return f"{prefix}-{count + 1:03d}"

    # ==================== 扣款/回滚 ====================

    @staticmethod
    async def _apply_adjustment(db: AsyncSession, order: PurchaseReturnOrder) -> None:
        """将售后金额累加到采购单的 after_sales_adjustment"""
        if order.refund_method != "deduct_payable" or not order.refund_amount:
            return
        if order.purchase_order_v2_id:
            result = await db.execute(
                select(PurchaseOrderV2).where(PurchaseOrderV2.id == order.purchase_order_v2_id)
            )
            po = result.scalar_one_or_none()
            if po:
                po.after_sales_adjustment = (po.after_sales_adjustment or Decimal("0")) + order.refund_amount
        elif order.material_purchase_order_id:
            result = await db.execute(
                select(MaterialPurchaseOrder).where(MaterialPurchaseOrder.id == order.material_purchase_order_id)
            )
            po = result.scalar_one_or_none()
            if po:
                po.after_sales_adjustment = (po.after_sales_adjustment or Decimal("0")) + order.refund_amount

    @staticmethod
    async def _revert_adjustment(db: AsyncSession, order: PurchaseReturnOrder) -> None:
        """从采购单的 after_sales_adjustment 减去售后金额（回滚）"""
        if order.refund_method != "deduct_payable" or not order.refund_amount:
            return
        if order.purchase_order_v2_id:
            result = await db.execute(
                select(PurchaseOrderV2).where(PurchaseOrderV2.id == order.purchase_order_v2_id)
            )
            po = result.scalar_one_or_none()
            if po:
                po.after_sales_adjustment = (po.after_sales_adjustment or Decimal("0")) - order.refund_amount
                if po.after_sales_adjustment < 0:
                    po.after_sales_adjustment = Decimal("0")
        elif order.material_purchase_order_id:
            result = await db.execute(
                select(MaterialPurchaseOrder).where(MaterialPurchaseOrder.id == order.material_purchase_order_id)
            )
            po = result.scalar_one_or_none()
            if po:
                po.after_sales_adjustment = (po.after_sales_adjustment or Decimal("0")) - order.refund_amount
                if po.after_sales_adjustment < 0:
                    po.after_sales_adjustment = Decimal("0")

    # ==================== 采购单查询（用于自动带出信息） ====================

    @staticmethod
    async def get_purchase_order_for_return(db: AsyncSession, order_type: str, order_id: int) -> dict:
        """获取采购单信息，用于创建售后单时自动带出"""
        if order_type == "purchase_v2":
            result = await db.execute(
                select(PurchaseOrderV2).where(PurchaseOrderV2.id == order_id)
            )
            po = result.scalar_one_or_none()
            if not po:
                raise ValueError("采购单不存在")

            # 查询明细的平均单价（用于默认填充）
            products_result = await db.execute(
                select(PurchaseOrderProductV2).where(
                    PurchaseOrderProductV2.purchase_order_id == order_id
                )
            )
            products = list(products_result.scalars().all())
            avg_unit_price = Decimal("0")
            if products:
                total_amount = sum(p.total_amount or Decimal("0") for p in products)
                total_weight = sum(p.weight_kg or Decimal("0") for p in products)
                if total_weight > 0:
                    avg_unit_price = (total_amount / total_weight).quantize(Decimal("0.0001"))

            return {
                "supplier_id": po.supplier_id,
                "supplier_name": po.supplier_name,
                "total_amount": po.total_amount,
                "products": products,
                "avg_unit_price": avg_unit_price,
            }
        else:
            # material_purchase
            from app.services.material_purchase_service import MaterialPurchaseService
            po = await MaterialPurchaseService.get_order(db, order_id)
            if not po:
                raise ValueError("采购单不存在")

            return {
                "supplier_id": po.supplier_id,
                "supplier_name": po.supplier_name,
                "total_amount": po.actual_total,
                "products": po.items,
                "avg_unit_price": Decimal("0"),
            }

    # ==================== CRUD ====================

    @staticmethod
    async def create_return_order(db: AsyncSession, data: dict, created_by_id: int | None = None) -> PurchaseReturnOrder:
        """创建采购售后单 — 创建后立即扣款"""
        return_no = await PurchaseReturnService._generate_return_no(db)

        # 处理日期：字符串转 date 对象
        return_date = data.get("return_date", date.today())
        if isinstance(return_date, str):
            return_date = date.fromisoformat(return_date)

        order = PurchaseReturnOrder(
            return_no=return_no,
            purchase_order_type=data["purchase_order_type"],
            purchase_order_v2_id=data.get("purchase_order_v2_id"),
            material_purchase_order_id=data.get("material_purchase_order_id"),
            return_date=return_date,
            supplier_id=data["supplier_id"],
            supplier_name=data.get("supplier_name"),
            refund_method=data.get("refund_method"),
            problem_description=data.get("problem_description"),
            supplier_feedback=data.get("supplier_feedback"),
            internal_notes=data.get("internal_notes"),
            created_by_id=created_by_id,
            status=PurchaseReturnStatus.COMPLETED,  # 直接生效，无需审批
        )
        db.add(order)
        await db.flush()

        # 创建明细
        items_data = data.get("items", [])
        total_weight = Decimal("0")
        total_amount = Decimal("0")

        for item_data in items_data:
            weight_kg = Decimal(str(item_data.get("weight_kg", 0)))
            unit_price = Decimal(str(item_data.get("unit_price", 0)))
            amount = (weight_kg * unit_price).quantize(Decimal("0.01"))

            item = PurchaseReturnItem(
                return_order_id=order.id,
                weight_kg=weight_kg,
                unit_price=unit_price,
                amount=amount,
                remarks=item_data.get("remarks"),
                purchase_order_product_v2_id=item_data.get("purchase_order_product_v2_id"),
                material_purchase_item_id=item_data.get("material_purchase_item_id"),
            )
            db.add(item)
            total_weight += weight_kg
            total_amount += amount

        order.total_weight_kg = total_weight
        order.total_amount = total_amount
        order.refund_amount = total_amount
        order.refund_date = date.today()

        # 立即扣款
        await PurchaseReturnService._apply_adjustment(db, order)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def get_return_order(db: AsyncSession, return_id: int) -> PurchaseReturnOrder | None:
        result = await db.execute(
            select(PurchaseReturnOrder).where(PurchaseReturnOrder.id == return_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_return_orders(
        db: AsyncSession,
        purchase_order_type: str | None = None,
        supplier_id: int | None = None,
        status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[PurchaseReturnOrder], int]:
        query = select(PurchaseReturnOrder)

        if purchase_order_type:
            query = query.where(PurchaseReturnOrder.purchase_order_type == purchase_order_type)
        if supplier_id:
            query = query.where(PurchaseReturnOrder.supplier_id == supplier_id)
        if status:
            query = query.where(PurchaseReturnOrder.status == status)
        if start_date:
            query = query.where(PurchaseReturnOrder.return_date >= start_date)
        if end_date:
            query = query.where(PurchaseReturnOrder.return_date <= end_date)
        if search:
            query = query.where(
                PurchaseReturnOrder.return_no.ilike(f"%{search}%") |
                PurchaseReturnOrder.problem_description.ilike(f"%{search}%")
            )

        query = query.order_by(desc(PurchaseReturnOrder.return_date), desc(PurchaseReturnOrder.id))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def update_return_order(db: AsyncSession, order: PurchaseReturnOrder, data: dict) -> PurchaseReturnOrder:
        """更新售后单 — 先回滚旧扣款，更新后再应用新扣款"""
        # 先回滚旧扣款
        await PurchaseReturnService._revert_adjustment(db, order)

        for key, value in data.items():
            if key == "items" and value is not None:
                # 更新明细：删除旧明细，创建新明细
                from sqlalchemy import delete
                await db.execute(
                    delete(PurchaseReturnItem).where(
                        PurchaseReturnItem.return_order_id == order.id
                    )
                )

                total_weight = Decimal("0")
                total_amount = Decimal("0")
                for item_data in value:
                    weight_kg = Decimal(str(item_data.get("weight_kg", 0)))
                    unit_price = Decimal(str(item_data.get("unit_price", 0)))
                    amount = (weight_kg * unit_price).quantize(Decimal("0.01"))

                    item = PurchaseReturnItem(
                        return_order_id=order.id,
                        weight_kg=weight_kg,
                        unit_price=unit_price,
                        amount=amount,
                        remarks=item_data.get("remarks"),
                        purchase_order_product_v2_id=item_data.get("purchase_order_product_v2_id"),
                        material_purchase_item_id=item_data.get("material_purchase_item_id"),
                    )
                    db.add(item)
                    total_weight += weight_kg
                    total_amount += amount

                order.total_weight_kg = total_weight
                order.total_amount = total_amount
                order.refund_amount = total_amount
            elif key == "return_date" and value is not None and isinstance(value, str):
                setattr(order, key, date.fromisoformat(value))
            elif hasattr(order, key) and value is not None:
                setattr(order, key, value)

        # 重新应用新扣款
        await PurchaseReturnService._apply_adjustment(db, order)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def delete_return_order(db: AsyncSession, order: PurchaseReturnOrder) -> None:
        """删除售后单 — 回滚扣款后删除"""
        # 回滚扣款
        await PurchaseReturnService._revert_adjustment(db, order)
        await db.delete(order)
        await db.commit()

    # ==================== 审批流程（已废弃，保留空实现兼容旧接口） ====================

    @staticmethod
    async def submit_for_approval(db: AsyncSession, order: PurchaseReturnOrder) -> PurchaseReturnOrder:
        """提交审批（已废弃）"""
        return order

    @staticmethod
    async def approve(db: AsyncSession, order: PurchaseReturnOrder, approved_by_id: int | None = None, notes: str | None = None) -> PurchaseReturnOrder:
        """审批（已废弃）"""
        return order

    @staticmethod
    async def reject(db: AsyncSession, order: PurchaseReturnOrder, approved_by_id: int | None = None, notes: str | None = None) -> PurchaseReturnOrder:
        """拒绝（已废弃）"""
        return order

    @staticmethod
    async def complete(db: AsyncSession, order: PurchaseReturnOrder, refund_date: date | None = None) -> PurchaseReturnOrder:
        """完成售后单（已废弃，创建时已自动完成）"""
        return order

    @staticmethod
    async def cancel(db: AsyncSession, order: PurchaseReturnOrder) -> PurchaseReturnOrder:
        """取消售后单（回滚扣款）"""
        await PurchaseReturnService._revert_adjustment(db, order)
        order.status = PurchaseReturnStatus.CANCELLED
        await db.commit()
        await db.refresh(order)
        return order

    # ==================== 附件管理 ====================

    @staticmethod
    async def add_attachment(db: AsyncSession, return_order_id: int, data: dict) -> PurchaseReturnAttachment:
        from app.models.purchase_returns import PurchaseReturnAttachmentType
        attachment = PurchaseReturnAttachment(
            return_order_id=return_order_id,
            file_type=PurchaseReturnAttachmentType(data["file_type"]),
            original_name=data["original_name"],
            file_name=data["file_name"],
            file_path=data["file_path"],
            file_size=data["file_size"],
            mime_type=data.get("mime_type"),
            description=data.get("description"),
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment

    @staticmethod
    async def delete_attachment(db: AsyncSession, attachment: PurchaseReturnAttachment) -> None:
        await db.delete(attachment)
        await db.commit()
