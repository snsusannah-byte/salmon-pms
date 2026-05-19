"""
采购入库模块 - Service
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Batch,
    Company,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    StockInbound,
    Warehouse,
)
from app.services.warehouse_v2_service import WarehouseV2Service


class PurchaseOrderService:
    """采购单服务"""

    # ==================== 采购单编号生成 ====================

    @staticmethod
    async def _generate_order_no(db: AsyncSession) -> str:
        today = date.today()
        prefix = f"CG{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.count()).select_from(
                select(PurchaseOrder).where(PurchaseOrder.order_no.like(f"{prefix}-%")).subquery()
            )
        )
        count = result.scalar() or 0
        return f"{prefix}-{count + 1:03d}"

    # ==================== CRUD ====================

    @staticmethod
    async def create_order(db: AsyncSession, data: dict) -> PurchaseOrder:
        """创建采购单"""
        order_no = await PurchaseOrderService._generate_order_no(db)

        order = PurchaseOrder(
            order_no=order_no,
            order_date=data.get("order_date", date.today()),
            supplier_id=data["supplier_id"],
            main_product_type=data["main_product_type"],
            main_warehouse_id=data["main_warehouse_id"],
            has_accessories=data.get("has_accessories", False),
            total_qty=Decimal(str(data.get("total_qty", 0))),
            total_amount=Decimal(str(data.get("total_amount", 0))),
            status=PurchaseOrderStatus.PENDING,
            notes=data.get("notes"),
        )
        db.add(order)
        await db.flush()  # 获取 order.id

        # 创建采购单项
        items = data.get("items", [])
        for item_data in items:
            item = PurchaseOrderItem(
                order_id=order.id,
                product_id=item_data["product_id"],
                batch_id=item_data.get("batch_id"),
                item_type=item_data.get("item_type", "main"),
                qty=Decimal(str(item_data["qty"])),
                unit=item_data["unit"],
                unit_price=Decimal(str(item_data["unit_price"])),
                total_amount=Decimal(str(item_data["qty"])) * Decimal(str(item_data["unit_price"])),
                warehouse_id=item_data.get("warehouse_id"),
                notes=item_data.get("notes"),
            )
            db.add(item)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def get_order(db: AsyncSession, order_id: int) -> Optional[PurchaseOrder]:
        result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        status: Optional[str] = None,
        supplier_id: Optional[int] = None,
        main_product_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[dict], int]:
        query = select(PurchaseOrder, Company, Warehouse).join(
            Company, PurchaseOrder.supplier_id == Company.id
        ).join(Warehouse, PurchaseOrder.main_warehouse_id == Warehouse.id)

        if status:
            query = query.where(PurchaseOrder.status == status)
        if supplier_id:
            query = query.where(PurchaseOrder.supplier_id == supplier_id)
        if main_product_type:
            query = query.where(PurchaseOrder.main_product_type == main_product_type)

        query = query.order_by(desc(PurchaseOrder.order_date), desc(PurchaseOrder.id))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        items = []
        for order, supplier, warehouse in rows:
            # 查询采购单项
            items_result = await db.execute(
                select(PurchaseOrderItem, Product).join(
                    Product, PurchaseOrderItem.product_id == Product.id
                ).where(PurchaseOrderItem.order_id == order.id)
            )
            order_items = []
            for item, product in items_result.all():
                order_items.append({
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": product.name,
                    "product_category": product.category,
                    "item_type": item.item_type,
                    "qty": item.qty,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "total_amount": item.total_amount,
                    "received_qty": item.received_qty,
                    "warehouse_id": item.warehouse_id,
                    "notes": item.notes,
                })

            items.append({
                "id": order.id,
                "order_no": order.order_no,
                "order_date": order.order_date,
                "supplier_id": order.supplier_id,
                "supplier_name": supplier.name,
                "main_product_type": order.main_product_type,
                "main_warehouse_id": order.main_warehouse_id,
                "warehouse_name": warehouse.name,
                "has_accessories": order.has_accessories,
                "total_qty": order.total_qty,
                "total_amount": order.total_amount,
                "status": order.status.value,
                "notes": order.notes,
                "items": order_items,
                "created_at": order.created_at,
                "updated_at": order.updated_at,
            })

        return items, total

    @staticmethod
    async def update_order(db: AsyncSession, order: PurchaseOrder, data: dict) -> PurchaseOrder:
        """更新采购单（仅待入库状态可修改）"""
        if order.status != PurchaseOrderStatus.PENDING:
            raise ValueError("只有待入库状态的采购单可以修改")

        for key, value in data.items():
            if value is not None and hasattr(order, key):
                setattr(order, key, value)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def cancel_order(db: AsyncSession, order: PurchaseOrder) -> PurchaseOrder:
        """取消采购单"""
        if order.status not in [PurchaseOrderStatus.PENDING, PurchaseOrderStatus.PARTIAL]:
            raise ValueError("只有待入库或部分入库的采购单可以取消")

        order.status = PurchaseOrderStatus.CANCELLED
        await db.commit()
        await db.refresh(order)
        return order

    # ==================== 入库确认 ====================

    @staticmethod
    async def confirm_inbound(db: AsyncSession, order_id: int, inbound_items: List[dict]) -> dict:
        """采购单入库确认"""
        order = await PurchaseOrderService.get_order(db, order_id)
        if not order:
            raise ValueError("采购单不存在")
        if order.status not in [PurchaseOrderStatus.PENDING, PurchaseOrderStatus.PARTIAL]:
            raise ValueError("采购单状态不允许入库")

        # 查询所有采购单项
        items_result = await db.execute(
            select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order_id)
        )
        order_items = list(items_result.scalars().all())

        total_inbound_qty = Decimal("0")
        inbound_records = []

        for inbound_data in inbound_items:
            item_id = inbound_data["item_id"]
            inbound_qty = Decimal(str(inbound_data["qty"]))

            # 查找对应的采购单项
            order_item = next((i for i in order_items if i.id == item_id), None)
            if not order_item:
                raise ValueError(f"采购单项 {item_id} 不存在")

            # 检查是否超收
            remaining = order_item.qty - order_item.received_qty
            if inbound_qty > remaining:
                raise ValueError(f"入库数量超过剩余数量：剩余 {remaining}，入库 {inbound_qty}")

            # 更新已入库数量
            order_item.received_qty += inbound_qty

            # 创建入库单（复用 warehouse_v2_service）
            warehouse_id = inbound_data.get("warehouse_id", order_item.warehouse_id or order.main_warehouse_id)
            inbound = await WarehouseV2Service.create_inbound(db, {
                "source_type": "purchase_order",
                "source_id": order.id,
                "source_no": order.order_no,
                "warehouse_id": warehouse_id,
                "product_id": order_item.product_id,
                "batch_id": order_item.batch_id,
                "qty": inbound_qty,
                "unit": order_item.unit,
                "unit_cost": order_item.unit_price,
                "supplier_id": order.supplier_id,
                "inbound_date": date.today(),
            })

            # 自动确认入库
            await WarehouseV2Service.confirm_inbound(db, inbound)

            total_inbound_qty += inbound_qty
            inbound_records.append(inbound.inbound_no)

        # 更新采购单状态
        total_received = sum(i.received_qty for i in order_items)
        total_ordered = sum(i.qty for i in order_items)

        if total_received >= total_ordered:
            order.status = PurchaseOrderStatus.COMPLETED
        elif total_received > 0:
            order.status = PurchaseOrderStatus.PARTIAL

        await db.commit()

        return {
            "order_id": order.id,
            "order_no": order.order_no,
            "status": order.status.value,
            "total_inbound_qty": total_inbound_qty,
            "inbound_records": inbound_records,
        }

    # ==================== 统计 ====================

    @staticmethod
    async def get_summary(db: AsyncSession) -> dict:
        """采购统计"""
        total_result = await db.execute(select(func.count()).select_from(PurchaseOrder))
        total = total_result.scalar()

        pending_result = await db.execute(
            select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.status == PurchaseOrderStatus.PENDING)
        )
        pending = pending_result.scalar()

        completed_result = await db.execute(
            select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.status == PurchaseOrderStatus.COMPLETED)
        )
        completed = completed_result.scalar()

        total_amount_result = await db.execute(
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0"))).where(
                PurchaseOrder.status != PurchaseOrderStatus.CANCELLED
            )
        )
        total_amount = total_amount_result.scalar()

        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "cancelled": total - pending - completed,
            "total_amount": total_amount,
        }
