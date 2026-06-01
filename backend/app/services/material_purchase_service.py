"""
物料采购与批次管理服务层
"""
from datetime import date
from decimal import Decimal, ROUND_CEILING
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import func, select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Company,
    MaterialBatch,
    MaterialPurchaseItem,
    MaterialPurchaseOrder,
    Product,
    Warehouse,
)
from app.services.warehouse_v2_service import WarehouseV2Service


class MaterialPurchaseService:
    """物料采购服务"""

    # ==================== 编号生成 ====================

    @staticmethod
    async def _generate_order_no(db: AsyncSession) -> str:
        today = date.today()
        prefix = f"CG{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.count()).select_from(
                select(MaterialPurchaseOrder).where(MaterialPurchaseOrder.order_no.like(f"{prefix}-%")).subquery()
            )
        )
        count = result.scalar() or 0
        return f"{prefix}-{count + 1:03d}"

    @staticmethod
    async def _generate_batch_no(product_code: str) -> str:
        today = date.today().strftime("%Y%m%d")
        suffix = uuid4().hex[:4]
        return f"BM-{product_code}-{today}-{suffix}"

    # ==================== 采购单 CRUD ====================

    @staticmethod
    async def create_order(db: AsyncSession, data: dict) -> MaterialPurchaseOrder:
        """创建物料采购单 — 状态为 pending（待入库），需手动执行入库操作"""
        items_data = data.get("items", [])
        if not items_data:
            raise ValueError("采购明细不能为空")

        # 校验金额一致性
        items_actual_sum = sum(Decimal(str(d.get("actual_amount", 0))) for d in items_data)
        actual_total = Decimal(str(data.get("actual_total", 0)))
        if items_actual_sum != actual_total:
            raise ValueError(f"实付金额不一致：明细之和 {items_actual_sum} ≠ 单头 {actual_total}")

        order_no = await MaterialPurchaseService._generate_order_no(db)

        order = MaterialPurchaseOrder(
            order_no=order_no,
            order_date=data.get("order_date", date.today()),
            supplier_id=data["supplier_id"],
            warehouse_id=data.get("warehouse_id"),
            quoted_total=Decimal(str(data.get("quoted_total", 0))) if data.get("quoted_total") else None,
            actual_total=actual_total,
            paid_amount=Decimal("0"),
            status="pending",
            payment_status="unpaid",
            inbound_date=None,
            notes=data.get("notes"),
        )
        db.add(order)
        await db.flush()

        # 创建采购明细
        order_items = []
        for item_data in items_data:
            product_id = item_data["product_id"]
            box_count = int(item_data["box_count"])
            items_per_box = int(item_data["items_per_box"])
            total_qty = Decimal(box_count * items_per_box)
            actual_amount = Decimal(str(item_data["actual_amount"]))
            actual_unit_price = (actual_amount / total_qty).quantize(Decimal("0.01"), rounding=ROUND_CEILING) if total_qty > 0 else Decimal("0")

            quoted_unit_price = Decimal(str(item_data["quoted_unit_price"])) if item_data.get("quoted_unit_price") else None
            quoted_amount = (total_qty * quoted_unit_price).quantize(Decimal("0.01")) if quoted_unit_price else None

            # 查询物料单位
            prod_result = await db.execute(select(Product.unit).where(Product.id == product_id))
            unit = prod_result.scalar() or "个"

            item = MaterialPurchaseItem(
                purchase_order_id=order.id,
                product_id=product_id,
                box_count=box_count,
                items_per_box=items_per_box,
                total_qty=total_qty,
                unit=unit,
                quoted_unit_price=quoted_unit_price,
                quoted_amount=quoted_amount,
                actual_amount=actual_amount,
                actual_unit_price=actual_unit_price,
                received_qty=Decimal("0"),
                is_fully_received=False,
                notes=item_data.get("notes"),
            )
            db.add(item)
            await db.flush()
            order_items.append((item, product_id, box_count, items_per_box, total_qty, unit, actual_amount, actual_unit_price))

        # 创建应付记录
        from app.models import PurchaseOrderV2, PurchaseOrderProductV2
        purchase_no = f"CGCL-{order.order_no}"
        supplier_result = await db.execute(select(Company.name).where(Company.id == order.supplier_id))
        supplier_name = supplier_result.scalar() or ""
        po_v2 = PurchaseOrderV2(
            purchase_no=purchase_no,
            purchase_date=order.order_date,
            supplier_id=order.supplier_id,
            supplier_name=supplier_name,
            total_amount=actual_total,
            total_weight=Decimal("0"),
            total_boxes=sum(box_count for _, _, box_count, _, _, _, _, _ in order_items),
            order_type="accessories",
            remark=order.notes,
            status="pending",
        )
        db.add(po_v2)
        await db.flush()

        # 创建采购明细
        for item, product_id, box_count, items_per_box, total_qty, unit, actual_amount, actual_unit_price in order_items:
            prod_result = await db.execute(
                select(Product.name, Product.spec).where(Product.id == product_id)
            )
            prod_name, prod_spec = prod_result.first() or ("未知物料", "")
            po_product = PurchaseOrderProductV2(
                purchase_order_id=po_v2.id,
                material_id=product_id,
                product_name=prod_name,
                product_spec=prod_spec or "",
                box_count=box_count,
                weight_kg=Decimal("0"),
                unit=unit,
                unit_price=actual_unit_price,
                total_amount=actual_amount,
            )
            db.add(po_product)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def get_order(db: AsyncSession, order_id: int) -> Optional[MaterialPurchaseOrder]:
        result = await db.execute(
            select(MaterialPurchaseOrder).where(MaterialPurchaseOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        supplier_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[dict], int]:
        query = (
            select(MaterialPurchaseOrder, Company)
            .join(Company, MaterialPurchaseOrder.supplier_id == Company.id)
        )

        if supplier_id:
            query = query.where(MaterialPurchaseOrder.supplier_id == supplier_id)
        if status:
            query = query.where(MaterialPurchaseOrder.status == status)
        if date_from:
            query = query.where(MaterialPurchaseOrder.order_date >= date_from)
        if date_to:
            query = query.where(MaterialPurchaseOrder.order_date <= date_to)

        query = query.order_by(desc(MaterialPurchaseOrder.order_date), desc(MaterialPurchaseOrder.id))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        items = []
        for order, supplier in rows:
            # 查询明细汇总
            items_result = await db.execute(
                select(MaterialPurchaseItem, Product)
                .join(Product, MaterialPurchaseItem.product_id == Product.id)
                .where(MaterialPurchaseItem.purchase_order_id == order.id)
            )
            order_items = items_result.all()
            item_count = len(order_items)
            
            # 汇总箱数、数量、单位、产品名称
            total_boxes = sum(item.box_count for item, _ in order_items)
            total_qty = sum(float(item.total_qty) for item, _ in order_items)
            unit = order_items[0][0].unit if order_items else "个"
            product_names = [prod.name for _, prod in order_items if prod.name]
            
            # 查询批次号
            batch_result = await db.execute(
                select(MaterialBatch.batch_no)
                .join(MaterialPurchaseItem, MaterialBatch.purchase_order_item_id == MaterialPurchaseItem.id)
                .where(MaterialPurchaseItem.purchase_order_id == order.id)
                .limit(1)
            )
            batch_no = batch_result.scalar()
            # 查询仓库名称
            warehouse_name = None
            if order.warehouse_id:
                wh_result = await db.execute(
                    select(Warehouse.name).where(Warehouse.id == order.warehouse_id)
                )
                warehouse_name = wh_result.scalar()
            # 计算到货周期（自然日）
            lead_time = None
            if order.inbound_date and order.order_date:
                lead_time = (order.inbound_date - order.order_date).days

            items.append({
                "id": order.id,
                "order_no": order.order_no,
                "order_date": order.order_date,
                "supplier_id": order.supplier_id,
                "supplier_name": supplier.name,
                "actual_total": order.actual_total,
                "status": order.status,
                "payment_status": order.payment_status,
                "item_count": item_count,
                "batch_no": batch_no,
                "warehouse_name": warehouse_name,
                "total_boxes": total_boxes,
                "total_qty": total_qty,
                "unit": unit,
                "product_names": product_names,
                "inbound_date": order.inbound_date,
                "lead_time": lead_time,
            })

        return items, total

    @staticmethod
    async def cancel_order(db: AsyncSession, order: MaterialPurchaseOrder) -> MaterialPurchaseOrder:
        if order.status != "pending":
            raise ValueError("只有待入库状态的采购单可以取消")
        order.status = "cancelled"
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def delete_order(db: AsyncSession, order: MaterialPurchaseOrder) -> None:
        """删除采购单（含关联数据完整清理）"""
        from app.models import MaterialBatch, MaterialPurchaseItem, PurchaseOrderV2, PurchaseOrderProductV2, TransactionRecord, StockInbound, StockMovement
        from sqlalchemy import delete, text, select

        # 1. 清理关联的批次和明细
        items_result = await db.execute(
            select(MaterialPurchaseItem).where(MaterialPurchaseItem.purchase_order_id == order.id)
        )
        order_items = items_result.scalars().all()

        for item in order_items:
            # 删除关联批次
            await db.execute(
                delete(MaterialBatch).where(MaterialBatch.purchase_order_item_id == item.id)
            )
            # 删除明细
            await db.delete(item)

        # 2. 删除库存变动记录（两种 ref_type 都要处理）
        # 先找到 StockInbound 记录，删除对应的 StockMovement
        inbound_result = await db.execute(
            select(StockInbound.id).where(
                StockInbound.source_type == "material_purchase",
                StockInbound.source_id == order.id
            )
        )
        inbound_ids = [r[0] for r in inbound_result.all()]
        if inbound_ids:
            await db.execute(
                delete(StockMovement).where(StockMovement.ref_id.in_(inbound_ids), StockMovement.ref_type == "StockInbound")
            )
        # 删除 material_purchase 类型的记录
        await db.execute(
            text("DELETE FROM stock_movements WHERE ref_type = 'material_purchase' AND ref_id = :order_id"),
            {"order_id": order.id}
        )

        # 3. 删除入库记录
        await db.execute(
            delete(StockInbound).where(
                StockInbound.source_type == "material_purchase",
                StockInbound.source_id == order.id
            )
        )

        # 4. 删除应付记录（先删子表，再删父表）
        po_v2_result = await db.execute(
            select(PurchaseOrderV2.id).where(PurchaseOrderV2.purchase_no == f"CGCL-{order.order_no}")
        )
        po_v2_id = po_v2_result.scalar_one_or_none()
        if po_v2_id:
            await db.execute(
                delete(PurchaseOrderProductV2).where(PurchaseOrderProductV2.purchase_order_id == po_v2_id)
            )
            await db.execute(
                delete(PurchaseOrderV2).where(PurchaseOrderV2.id == po_v2_id)
            )

        # 5. 删除交易流水
        await db.execute(
            delete(TransactionRecord).where(TransactionRecord.reference_no == order.order_no)
        )

        # 6. 删除采购单
        await db.delete(order)
        await db.commit()

    # ==================== 入库 ====================

    @staticmethod
    async def confirm_inbound(db: AsyncSession, order_id: int, inbound_data: List[dict]) -> dict:
        """采购单入库确认 — 支持部分入库、多次入库"""
        order = await MaterialPurchaseService.get_order(db, order_id)
        if not order:
            raise ValueError("采购单不存在")
        if order.status not in ["pending", "partial_inbound"]:
            raise ValueError("采购单状态不允许入库")

        # 查询所有采购明细
        items_result = await db.execute(
            select(MaterialPurchaseItem).where(MaterialPurchaseItem.purchase_order_id == order_id)
        )
        order_items = {item.id: item for item in items_result.scalars().all()}

        inbound_records = []
        total_inbound_qty = Decimal("0")
        
        # 入库日期（默认今天，可传入自定义日期）
        inbound_date = None
        for inbound_item in inbound_data:
            if inbound_item.get("inbound_date"):
                inbound_date = date.fromisoformat(inbound_item["inbound_date"])
                break
        if not inbound_date:
            inbound_date = date.today()
        
        # 记录第一次入库日期（用于计算到货周期）
        if not order.inbound_date:
            order.inbound_date = inbound_date

        for inbound_item in inbound_data:
            item_id = inbound_item["item_id"]
            inbound_qty = Decimal(str(inbound_item.get("inbound_qty", 0)))

            if item_id not in order_items:
                raise ValueError(f"采购明细 {item_id} 不存在")

            order_item = order_items[item_id]
            remaining = order_item.total_qty - order_item.received_qty
            if inbound_qty > remaining:
                raise ValueError(f"入库数量超过剩余数量：剩余 {remaining}，入库 {inbound_qty}")
            if inbound_qty <= 0:
                continue

            # 更新已入库数量
            order_item.received_qty = (order_item.received_qty + inbound_qty).quantize(Decimal("0.001"))
            if order_item.received_qty >= order_item.total_qty:
                order_item.is_fully_received = True

            # 查询物料编码
            prod_result = await db.execute(
                select(Product.code, Product.name).where(Product.id == order_item.product_id)
            )
            product_code, product_name = prod_result.first() or ("UNKNOWN", "未知物料")

            # 查询供应商名称
            supplier_result = await db.execute(
                select(Company.name).where(Company.id == order.supplier_id)
            )
            supplier_name = supplier_result.scalar() or ""

            # 生成批次
            batch_no = await MaterialPurchaseService._generate_batch_no(product_code)
            batch = MaterialBatch(
                batch_no=batch_no,
                product_id=order_item.product_id,
                supplier_name=supplier_name,
                purchase_order_item_id=order_item.id,
                inbound_qty=inbound_qty,
                remaining_qty=inbound_qty,
                unit=order_item.unit,
                unit_cost=order_item.actual_unit_price,
                total_cost=(inbound_qty * order_item.actual_unit_price).quantize(Decimal("0.01")),
                inbound_date=inbound_date,
                expiry_date=inbound_item.get("expiry_date"),
                warehouse_id=order.warehouse_id,
                location=inbound_item.get("location"),
                status="active",
            )
            db.add(batch)
            await db.flush()

            # 调用仓库服务更新总库存
            warehouse_inbound = await WarehouseV2Service.create_inbound(db, {
                "source_type": "material_purchase",
                "source_id": order.id,
                "source_no": order.order_no,
                "warehouse_id": order.warehouse_id,
                "product_id": order_item.product_id,
                "qty": inbound_qty,
                "unit": order_item.unit,
                "unit_cost": order_item.actual_unit_price,
                "supplier_id": order.supplier_id,
                "inbound_date": inbound_date,
                "notes": f"物料采购入库：{batch_no}",
            })
            await WarehouseV2Service.confirm_inbound(db, warehouse_inbound)

            inbound_records.append({
                "item_id": item_id,
                "batch_no": batch_no,
                "inbound_qty": inbound_qty,
            })
            total_inbound_qty += inbound_qty

        # 更新采购单状态
        all_fully_received = all(item.is_fully_received for item in order_items.values())
        any_received = any(item.received_qty > 0 for item in order_items.values())
        if all_fully_received:
            order.status = "completed"
        elif any_received:
            order.status = "partial_inbound"

        # 更新 PurchaseOrderV2 状态
        if all_fully_received:
            from app.models import PurchaseOrderV2
            po_result = await db.execute(
                select(PurchaseOrderV2).where(PurchaseOrderV2.purchase_no == f"CGCL-{order.order_no}")
            )
            po_v2 = po_result.scalar_one_or_none()
            if po_v2:
                po_v2.status = "completed"

        await db.commit()

        return {
            "order_id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "inbound_date": order.inbound_date.isoformat() if order.inbound_date else None,
            "total_inbound_qty": total_inbound_qty,
            "inbound_records": inbound_records,
        }

    # ==================== 出库 ====================

    @staticmethod
    async def fifo_outbound(db: AsyncSession, product_id: int, qty: Decimal) -> List[dict]:
        """FIFO 先进先出出库"""
        if qty <= 0:
            raise ValueError("出库数量必须大于0")

        result = await db.execute(
            select(MaterialBatch)
            .where(
                and_(
                    MaterialBatch.product_id == product_id,
                    MaterialBatch.remaining_qty > 0,
                    MaterialBatch.status == "active",
                )
            )
            .order_by(MaterialBatch.inbound_date.asc())
        )
        batches = list(result.scalars().all())

        allocations = []
        remaining = qty
        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.remaining_qty, remaining)
            batch.remaining_qty = (batch.remaining_qty - take).quantize(Decimal("0.001"))
            if batch.remaining_qty <= 0:
                batch.status = "empty"

            allocations.append({
                "batch_id": batch.id,
                "batch_no": batch.batch_no,
                "qty": take,
                "unit_cost": batch.unit_cost,
                "supplier_name": batch.supplier_name,
            })
            remaining -= take

        if remaining > 0:
            raise ValueError(f"库存不足，缺 {remaining}")

        return allocations

    @staticmethod
    async def specific_batch_outbound(db: AsyncSession, batch_id: int, qty: Decimal) -> dict:
        """指定批次出库"""
        if qty <= 0:
            raise ValueError("出库数量必须大于0")

        result = await db.execute(select(MaterialBatch).where(MaterialBatch.id == batch_id))
        batch = result.scalar_one_or_none()
        if not batch:
            raise ValueError("批次不存在")
        if batch.remaining_qty < qty:
            raise ValueError(f"批次 {batch.batch_no} 只有 {batch.remaining_qty}")

        batch.remaining_qty = (batch.remaining_qty - qty).quantize(Decimal("0.001"))
        if batch.remaining_qty <= 0:
            batch.status = "empty"

        return {
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            "qty": qty,
            "unit_cost": batch.unit_cost,
            "supplier_name": batch.supplier_name,
        }

    @staticmethod
    async def confirm_outbound(db: AsyncSession, product_id: int, qty: Decimal, allocations: List[dict], warehouse_id: int, reason: Optional[str] = None) -> dict:
        """确认出库并更新仓库库存"""
        prod_result = await db.execute(select(Product).where(Product.id == product_id))
        product = prod_result.scalar_one_or_none()
        if not product:
            raise ValueError("物料不存在")

        total_cost = Decimal("0")
        for alloc in allocations:
            total_cost += alloc["qty"] * alloc["unit_cost"]

        # 调用仓库服务出库
        warehouse_outbound = await WarehouseV2Service.create_outbound(db, {
            "dest_type": "material_consumption",
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "qty": qty,
            "outbound_date": date.today(),
            "notes": reason or "物料出库",
        })
        await WarehouseV2Service.confirm_outbound(db, warehouse_outbound)

        avg_cost = (total_cost / qty).quantize(Decimal("0.0001")) if qty > 0 else Decimal("0")

        return {
            "product_id": product_id,
            "product_name": product.name,
            "total_qty": qty,
            "allocations": allocations,
            "avg_cost": avg_cost,
        }

    # ==================== 库存查询 ====================

    @staticmethod
    async def get_stock(db: AsyncSession, product_id: int) -> dict:
        """获取物料库存（总库存 + 批次明细）"""
        prod_result = await db.execute(select(Product).where(Product.id == product_id))
        product = prod_result.scalar_one_or_none()
        if not product:
            raise ValueError("物料不存在")

        # 批次明细
        batch_result = await db.execute(
            select(MaterialBatch)
            .where(
                and_(
                    MaterialBatch.product_id == product_id,
                    MaterialBatch.status == "active",
                    MaterialBatch.remaining_qty > 0,
                )
            )
            .order_by(MaterialBatch.inbound_date.asc())
        )
        batches = list(batch_result.scalars().all())

        total_qty = sum(b.remaining_qty for b in batches)
        total_cost = sum(b.remaining_qty * b.unit_cost for b in batches)
        avg_cost = (total_cost / total_qty).quantize(Decimal("0.0001")) if total_qty > 0 else Decimal("0")

        return {
            "product_id": product_id,
            "product_code": product.code,
            "product_name": product.name,
            "spec": product.spec,
            "unit": product.unit,
            "items_per_box": product.items_per_box,
            "total_qty": total_qty,
            "batch_count": len(batches),
            "avg_cost": avg_cost,
            "batches": [
                {
                    "id": b.id,
                    "batch_no": b.batch_no,
                    "supplier_name": b.supplier_name,
                    "remaining_qty": b.remaining_qty,
                    "unit_cost": b.unit_cost,
                    "total_cost": b.remaining_qty * b.unit_cost,
                    "inbound_date": b.inbound_date,
                    "expiry_date": b.expiry_date,
                    "status": b.status,
                }
                for b in batches
            ],
        }

    @staticmethod
    async def list_materials_with_stock(
        db: AsyncSession,
        category_id: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> List[dict]:
        """物料列表（含库存汇总）"""
        query = select(Product).where(Product.category == "bom_material")

        if category_id:
            query = query.where(Product.material_category_id == category_id)
        if keyword:
            query = query.where(
                Product.name.ilike(f"%{keyword}%") | Product.code.ilike(f"%{keyword}%")
            )

        query = query.where(Product.is_active == True).order_by(Product.code)

        result = await db.execute(query)
        products = list(result.scalars().all())

        items = []
        for product in products:
            stock = await MaterialPurchaseService.get_stock(db, product.id)
            items.append({
                "id": product.id,
                "code": product.code,
                "name": product.name,
                "spec": product.spec,
                "unit": product.unit,
                "items_per_box": product.items_per_box,
                "material_category_id": product.material_category_id,
                "total_qty": stock["total_qty"],
                "batch_count": stock["batch_count"],
                "avg_cost": stock["avg_cost"],
                "is_active": product.is_active,
            })

        return items
