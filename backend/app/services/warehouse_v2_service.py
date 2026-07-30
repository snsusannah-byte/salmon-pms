"""
仓库模块V2 - Service
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Batch,
    Product,
    Stock,
    StockInbound,
    StockMovement,
    StockMovementType,
    StockOutbound,
    StockStatus,
    StockTransfer,
    Warehouse,
)
from app.models.enums import WarehouseType
from app.models.product import ProductCategory


class WarehouseV2Service:
    """仓库模块V2服务"""

    # ==================== 仓库管理 ====================

    @staticmethod
    async def list_warehouses(
        db: AsyncSession,
        type: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Warehouse], int]:
        query = select(Warehouse)
        if type:
            query = query.where(Warehouse.type == type)
        if is_active is not None:
            query = query.where(Warehouse.is_active == is_active)
        query = query.order_by(Warehouse.code)

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def get_warehouse(db: AsyncSession, warehouse_id: int) -> Warehouse | None:
        result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_warehouse_by_code(db: AsyncSession, code: str) -> Warehouse | None:
        result = await db.execute(select(Warehouse).where(Warehouse.code == code))
        return result.scalar_one_or_none()

    # ==================== 仓库类型校验 ====================

    @staticmethod
    def get_warehouse_type_for_product(category: str) -> list[str]:
        """根据产品分类获取允许的仓库类型"""
        mapping = {
            ProductCategory.WHOLE_FISH.value: [WarehouseType.WHOLE_PACKAGE.value],
            ProductCategory.FILLET.value: [WarehouseType.WHOLE_PACKAGE.value],
            ProductCategory.FINISHED_PRODUCT.value: [WarehouseType.FINISHED.value],
            ProductCategory.BYPRODUCT.value: [WarehouseType.BYPRODUCT.value],
            ProductCategory.PACKAGING.value: [WarehouseType.ACCESSORY.value],
            ProductCategory.ACCESSORY.value: [WarehouseType.ACCESSORY.value],
            ProductCategory.BOM_MATERIAL.value: [WarehouseType.ACCESSORY.value],
        }
        return mapping.get(category, [WarehouseType.WHOLE_PACKAGE.value])

    @staticmethod
    def validate_product_warehouse_match(product_category: str, warehouse_type: str) -> bool:
        """校验产品分类和仓库类型是否匹配"""
        allowed = WarehouseV2Service.get_warehouse_type_for_product(product_category)
        return warehouse_type in allowed

    @staticmethod
    async def get_default_warehouse_for_product(
        db: AsyncSession, product_id: int, scope: str = "import"
    ) -> Warehouse | None:
        """根据产品自动选择默认仓库"""
        # 查询产品分类
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            return None

        allowed_types = WarehouseV2Service.get_warehouse_type_for_product(product.category)

        # 查找匹配的仓库
        query = select(Warehouse).where(
            Warehouse.type.in_(allowed_types),
            Warehouse.is_active == True,
        )
        if scope == "import":
            # 优先找进口业务范围
            query = query.where(Warehouse.business_scope.in_(["IMPORT", "ALL"]))
        else:
            # 优先找国内业务范围
            query = query.where(Warehouse.business_scope.in_(["DOMESTIC", "ALL"]))

        query = query.order_by(Warehouse.code)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_warehouse(db: AsyncSession, data: dict) -> Warehouse:
        wh = Warehouse(**data)
        db.add(wh)
        await db.commit()
        await db.refresh(wh)
        return wh

    @staticmethod
    async def update_warehouse(db: AsyncSession, wh: Warehouse, data: dict) -> Warehouse:
        for k, v in data.items():
            if v is not None:
                setattr(wh, k, v)
        await db.commit()
        await db.refresh(wh)
        return wh

    # ==================== 库存管理 ====================

    @staticmethod
    async def get_or_create_stock(
        db: AsyncSession,
        warehouse_id: int,
        product_id: int,
        batch_id: int | None = None,
        batch_no: str | None = None,
        unit: str = "kg",
    ) -> Stock:
        result = await db.execute(
            select(Stock).where(
                Stock.warehouse_id == warehouse_id,
                Stock.product_id == product_id,
                Stock.batch_id == batch_id,
                Stock.batch_no == batch_no,
            )
        )
        stock = result.scalar_one_or_none()
        if not stock:
            stock = Stock(
                warehouse_id=warehouse_id,
                product_id=product_id,
                batch_id=batch_id,
                batch_no=batch_no,
                current_qty=Decimal("0"),
                reserved_qty=Decimal("0"),
                available_qty=Decimal("0"),
                current_box_count=0,
                available_box_count=0,
                unit=unit,
            )
            db.add(stock)
            await db.commit()
            await db.refresh(stock)
        return stock

    @staticmethod
    async def list_stocks(
        db: AsyncSession,
        warehouse_id: int | None = None,
        product_id: int | None = None,
        batch_id: int | None = None,
        is_below_warning: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        query = select(Stock, Warehouse, Product).join(
            Warehouse, Stock.warehouse_id == Warehouse.id
        ).join(Product, Stock.product_id == Product.id)

        if warehouse_id:
            query = query.where(Stock.warehouse_id == warehouse_id)
        if product_id:
            query = query.where(Stock.product_id == product_id)
        if batch_id:
            query = query.where(Stock.batch_id == batch_id)
        if is_below_warning is not None:
            query = query.where(Stock.is_below_warning == is_below_warning)

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        items = []
        for stock, wh, product in rows:
            batch_no = stock.batch_no
            if not batch_no and stock.batch_id:
                batch_result = await db.execute(select(Batch.batch_code).where(Batch.id == stock.batch_id))
                batch_no = batch_result.scalar()

            # 查询该产品最新入库的到货周期
            lead_time = None
            from app.models import MaterialPurchaseItem, MaterialPurchaseOrder
            mpo_result = await db.execute(
                select(MaterialPurchaseOrder)
                .join(MaterialPurchaseItem, MaterialPurchaseItem.purchase_order_id == MaterialPurchaseOrder.id)
                .where(
                    MaterialPurchaseItem.product_id == stock.product_id,
                    MaterialPurchaseOrder.inbound_date.is_not(None),
                )
                .order_by(desc(MaterialPurchaseOrder.inbound_date))
                .limit(1)
            )
            latest_order = mpo_result.scalar_one_or_none()
            if latest_order and latest_order.inbound_date and latest_order.order_date:
                lead_time = (latest_order.inbound_date - latest_order.order_date).days

            # 查询该产品在该仓库的所有历史批次号（从入库记录）
            batch_nos = []
            inbound_batch_result = await db.execute(
                select(StockInbound.batch_no).distinct()
                .where(
                    StockInbound.warehouse_id == stock.warehouse_id,
                    StockInbound.product_id == stock.product_id,
                    StockInbound.batch_no.is_not(None),
                )
                .order_by(StockInbound.batch_no)
            )
            batch_nos = [b for b in inbound_batch_result.scalars().all() if b]

            items.append({
                "id": stock.id,
                "warehouse_id": stock.warehouse_id,
                "warehouse_name": wh.name,
                "product_id": stock.product_id,
                "product_name": product.name,
                "product_spec": product.spec,
                "product_category": product.category,
                "batch_id": stock.batch_id,
                "batch_no": batch_no,
                "batch_nos": batch_nos,
                "current_qty": stock.current_qty,
                "current_box_count": stock.current_box_count,
                "available_box_count": stock.available_box_count,
                "reserved_qty": stock.reserved_qty,
                "available_qty": stock.available_qty,
                "unit_cost": stock.unit_cost,
                "total_cost": stock.total_cost,
                "unit": stock.unit,
                "warning_threshold": stock.warning_threshold,
                "is_below_warning": stock.is_below_warning,
                "last_in_date": stock.last_in_date,
                "last_out_date": stock.last_out_date,
                "location": stock.location,
                "notes": stock.notes,
                "lead_time": lead_time,
                "created_at": stock.created_at,
                "updated_at": stock.updated_at,
            })
        return items, total

    @staticmethod
    async def stock_summary(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                Warehouse.id,
                Warehouse.name,
                Warehouse.type,
                func.count(Stock.id).label("product_count"),
                func.coalesce(func.sum(Stock.current_qty), Decimal("0")).label("total_qty"),
                func.coalesce(func.sum(Stock.total_cost), Decimal("0")).label("total_cost"),
            )
            .join(Stock, Warehouse.id == Stock.warehouse_id, isouter=True)
            .group_by(Warehouse.id, Warehouse.name, Warehouse.type)
            .order_by(Warehouse.code)
        )
        rows = result.all()
        return [
            {
                "warehouse_id": r.id,
                "warehouse_name": r.name,
                "warehouse_type": r.type,
                "product_count": r.product_count,
                "total_qty": r.total_qty,
                "total_cost": r.total_cost,
            }
            for r in rows
        ]

    # ==================== 入库管理 ====================

    @staticmethod
    async def create_inbound(db: AsyncSession, data: dict) -> StockInbound:
        today = data.get("inbound_date", date.today())
        prefix = f"RK{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.count()).select_from(
                select(StockInbound).where(StockInbound.inbound_no.like(f"{prefix}-%")).subquery()
            )
        )
        count = result.scalar() or 0
        inbound_no = f"{prefix}-{count + 1:03d}"

        inbound = StockInbound(
            inbound_no=inbound_no,
            source_type=data["source_type"],
            source_id=data.get("source_id"),
            source_no=data.get("source_no"),
            warehouse_id=data["warehouse_id"],
            product_id=data["product_id"],
            batch_id=data.get("batch_id"),
            batch_no=data.get("batch_no"),
            qty=Decimal(str(data["qty"])),
            unit=data["unit"],
            unit_cost=Decimal(str(data["unit_cost"])),
            total_cost=Decimal(str(data["unit_cost"])) * Decimal(str(data["qty"])),
            supplier_id=data.get("supplier_id"),
            detail=data.get("detail"),
            inbound_date=data.get("inbound_date", date.today()),
            status=StockStatus.PENDING,
            notes=data.get("notes"),
        )
        db.add(inbound)
        await db.commit()
        await db.refresh(inbound)
        return inbound

    @staticmethod
    async def confirm_inbound(db: AsyncSession, inbound: StockInbound) -> Stock:
        if inbound.status != StockStatus.PENDING:
            raise ValueError("只有待确认的入库单可以确认")

        # 校验产品分类和仓库类型是否匹配
        product_result = await db.execute(select(Product).where(Product.id == inbound.product_id))
        product = product_result.scalar_one_or_none()
        if product:
            warehouse_result = await db.execute(select(Warehouse).where(Warehouse.id == inbound.warehouse_id))
            warehouse = warehouse_result.scalar_one_or_none()
            if warehouse and not WarehouseV2Service.validate_product_warehouse_match(
                product.category, warehouse.type.value
            ):
                allowed_types = WarehouseV2Service.get_warehouse_type_for_product(product.category)
                type_labels = {
                    WarehouseType.WHOLE_PACKAGE.value: "整包仓",
                    WarehouseType.SUB_PACKAGE.value: "分包仓",
                    WarehouseType.ACCESSORY.value: "辅料仓",
                    WarehouseType.BYPRODUCT.value: "副产品仓",
                    WarehouseType.FINISHED.value: "成品仓",
                }
                allowed_labels = [type_labels.get(t, t) for t in allowed_types]
                raise ValueError(
                    f"产品「{product.name}」属于{product.category}，"
                    f"只能入{', '.join(allowed_labels)}，"
                    f"不能入「{warehouse.name}」({type_labels.get(warehouse.type.value, warehouse.type.value)})"
                )

        stock = await WarehouseV2Service.get_or_create_stock(
            db, inbound.warehouse_id, inbound.product_id, inbound.batch_id, inbound.batch_no, inbound.unit
        )

        qty_before = stock.current_qty
        box_count_before = stock.current_box_count

        stock.current_qty = (stock.current_qty + inbound.qty).quantize(Decimal("0.001"))
        stock.available_qty = (stock.current_qty - stock.reserved_qty).quantize(Decimal("0.001"))
        stock.last_in_date = inbound.inbound_date
        stock.batch_no = inbound.batch_no or stock.batch_no

        # 更新箱数
        inbound_box_count = inbound.original_box_count or 0
        stock.current_box_count = stock.current_box_count + inbound_box_count
        stock.available_box_count = stock.current_box_count

        old_total = qty_before * (stock.unit_cost or Decimal("0"))
        new_total = inbound.qty * inbound.unit_cost
        if stock.current_qty > 0:
            stock.unit_cost = ((old_total + new_total) / stock.current_qty).quantize(Decimal("0.0001"))
        stock.total_cost = (stock.current_qty * (stock.unit_cost or Decimal("0"))).quantize(Decimal("0.01"))

        inbound.status = StockStatus.COMPLETED
        inbound.confirmed_at = func.now()
        inbound.remaining_box_count = inbound.original_box_count
        inbound.remaining_qty = inbound.qty

        movement = StockMovement(
            warehouse_id=inbound.warehouse_id,
            product_id=inbound.product_id,
            batch_id=inbound.batch_id,
            batch_no=inbound.batch_no,
            movement_type=StockMovementType.INBOUND,
            movement_date=inbound.inbound_date,
            qty_change=inbound.qty,
            qty_before=qty_before,
            qty_after=stock.current_qty,
            unit=inbound.unit,
            unit_cost=inbound.unit_cost,
            total_cost=inbound.total_cost,
            ref_type="StockInbound",
            ref_id=inbound.id,
            ref_no=inbound.inbound_no,
            box_count_change=inbound_box_count,
            box_count_before=box_count_before,
            box_count_after=stock.current_box_count,
        )
        db.add(movement)
        await db.commit()
        await db.refresh(stock)
        return stock

    @staticmethod
    async def list_inbounds(
        db: AsyncSession,
        warehouse_id: int | None = None,
        product_id: int | None = None,
        status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        query = select(StockInbound, Warehouse, Product).join(
            Warehouse, StockInbound.warehouse_id == Warehouse.id
        ).join(Product, StockInbound.product_id == Product.id)

        if warehouse_id:
            query = query.where(StockInbound.warehouse_id == warehouse_id)
        if product_id:
            query = query.where(StockInbound.product_id == product_id)
        if status:
            query = query.where(StockInbound.status == status)
        if start_date:
            query = query.where(StockInbound.inbound_date >= start_date)
        if end_date:
            query = query.where(StockInbound.inbound_date <= end_date)

        query = query.order_by(desc(StockInbound.inbound_date))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        items = []
        for inbound, wh, product in rows:
            items.append({
                "id": inbound.id,
                "inbound_no": inbound.inbound_no,
                "source_type": inbound.source_type,
                "source_id": inbound.source_id,
                "source_no": inbound.source_no,
                "warehouse_id": inbound.warehouse_id,
                "warehouse_name": wh.name,
                "product_id": inbound.product_id,
                "product_name": product.name,
                "batch_id": inbound.batch_id,
                "batch_no": inbound.batch_no,
                "qty": inbound.qty,
                "unit": inbound.unit,
                "unit_cost": inbound.unit_cost,
                "total_cost": inbound.total_cost,
                "supplier_id": inbound.supplier_id,
                "detail": inbound.detail,
                "status": inbound.status.value,
                "inbound_date": inbound.inbound_date,
                "confirmed_at": inbound.confirmed_at,
                "notes": inbound.notes,
                "created_at": inbound.created_at,
                "updated_at": inbound.updated_at,
            })
        return items, total

    @staticmethod
    async def get_inbound(db: AsyncSession, inbound_id: int) -> StockInbound | None:
        result = await db.execute(select(StockInbound).where(StockInbound.id == inbound_id))
        return result.scalar_one_or_none()

    # ==================== 出库管理 ====================

    @staticmethod
    async def create_outbound(db: AsyncSession, data: dict) -> StockOutbound:
        today = data.get("outbound_date", date.today())
        prefix = f"CK{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.count()).select_from(
                select(StockOutbound).where(StockOutbound.outbound_no.like(f"{prefix}-%")).subquery()
            )
        )
        count = result.scalar() or 0
        outbound_no = f"{prefix}-{count + 1:03d}"

        outbound = StockOutbound(
            outbound_no=outbound_no,
            dest_type=data["dest_type"],
            dest_id=data.get("dest_id"),
            dest_no=data.get("dest_no"),
            warehouse_id=data["warehouse_id"],
            product_id=data["product_id"],
            batch_id=data.get("batch_id"),
            qty=Decimal(str(data["qty"])),
            unit=data["unit"],
            box_count=data.get("box_count", 0),
            outbound_date=data.get("outbound_date", date.today()),
            status=StockStatus.PENDING,
            notes=data.get("notes"),
        )
        db.add(outbound)
        await db.commit()
        await db.refresh(outbound)
        return outbound

    @staticmethod
    async def confirm_outbound(db: AsyncSession, outbound: StockOutbound) -> Stock:
        if outbound.status != StockStatus.PENDING:
            raise ValueError("只有待确认的出库单可以确认")

        stock = await WarehouseV2Service.get_or_create_stock(
            db, outbound.warehouse_id, outbound.product_id, outbound.batch_id, outbound.unit
        )

        # 进口整包仓：以箱数为准，重量可以为负
        if stock.available_box_count < outbound.box_count:
            raise ValueError(f"箱数不足：可用{stock.available_box_count}箱，需要{outbound.box_count}箱")

        qty_before = stock.current_qty
        box_count_before = stock.current_box_count

        stock.current_qty = (stock.current_qty - outbound.qty).quantize(Decimal("0.001"))
        stock.available_qty = (stock.current_qty - stock.reserved_qty).quantize(Decimal("0.001"))
        stock.last_out_date = outbound.outbound_date

        # 扣减箱数
        stock.current_box_count = stock.current_box_count - outbound.box_count
        stock.available_box_count = stock.current_box_count

        outbound.unit_cost = stock.unit_cost
        outbound.total_cost = (outbound.qty * (stock.unit_cost or Decimal("0"))).quantize(Decimal("0.01"))

        if stock.current_qty > 0:
            stock.total_cost = (stock.current_qty * (stock.unit_cost or Decimal("0"))).quantize(Decimal("0.01"))
        else:
            stock.unit_cost = None
            stock.total_cost = Decimal("0")

        outbound.status = StockStatus.COMPLETED
        outbound.confirmed_at = func.now()

        movement = StockMovement(
            warehouse_id=outbound.warehouse_id,
            product_id=outbound.product_id,
            batch_id=outbound.batch_id,
            batch_no=None,
            movement_type=StockMovementType.OUTBOUND,
            movement_date=outbound.outbound_date,
            qty_change=-outbound.qty,
            qty_before=qty_before,
            qty_after=stock.current_qty,
            unit=outbound.unit,
            unit_cost=outbound.unit_cost,
            total_cost=outbound.total_cost,
            ref_type="StockOutbound",
            ref_id=outbound.id,
            ref_no=outbound.outbound_no,
            box_count_change=-outbound.box_count,
            box_count_before=box_count_before,
            box_count_after=stock.current_box_count,
        )
        db.add(movement)
        await db.commit()
        await db.refresh(stock)
        return stock

    @staticmethod
    async def list_outbounds(
        db: AsyncSession,
        warehouse_id: int | None = None,
        product_id: int | None = None,
        status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        query = select(StockOutbound, Warehouse, Product).join(
            Warehouse, StockOutbound.warehouse_id == Warehouse.id
        ).join(Product, StockOutbound.product_id == Product.id)

        if warehouse_id:
            query = query.where(StockOutbound.warehouse_id == warehouse_id)
        if product_id:
            query = query.where(StockOutbound.product_id == product_id)
        if status:
            query = query.where(StockOutbound.status == status)
        if start_date:
            query = query.where(StockOutbound.outbound_date >= start_date)
        if end_date:
            query = query.where(StockOutbound.outbound_date <= end_date)

        query = query.order_by(desc(StockOutbound.outbound_date))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        items = []
        for outbound, wh, product in rows:
            items.append({
                "id": outbound.id,
                "outbound_no": outbound.outbound_no,
                "dest_type": outbound.dest_type,
                "dest_id": outbound.dest_id,
                "dest_no": outbound.dest_no,
                "warehouse_id": outbound.warehouse_id,
                "warehouse_name": wh.name,
                "product_id": outbound.product_id,
                "product_name": product.name,
                "batch_id": outbound.batch_id,
                "qty": outbound.qty,
                "unit": outbound.unit,
                "unit_cost": outbound.unit_cost,
                "total_cost": outbound.total_cost,
                "status": outbound.status.value,
                "outbound_date": outbound.outbound_date,
                "confirmed_at": outbound.confirmed_at,
                "notes": outbound.notes,
                "created_at": outbound.created_at,
                "updated_at": outbound.updated_at,
            })
        return items, total

    @staticmethod
    async def get_outbound(db: AsyncSession, outbound_id: int) -> StockOutbound | None:
        result = await db.execute(select(StockOutbound).where(StockOutbound.id == outbound_id))
        return result.scalar_one_or_none()

    # ==================== 调拨管理 ====================

    @staticmethod
    async def create_transfer(db: AsyncSession, data: dict) -> StockTransfer:
        today = data.get("transfer_date", date.today())
        prefix = f"DB{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.count()).select_from(
                select(StockTransfer).where(StockTransfer.transfer_no.like(f"{prefix}-%")).subquery()
            )
        )
        count = result.scalar() or 0
        transfer_no = f"{prefix}-{count + 1:03d}"

        transfer = StockTransfer(
            transfer_no=transfer_no,
            from_warehouse_id=data["from_warehouse_id"],
            to_warehouse_id=data["to_warehouse_id"],
            product_id=data["product_id"],
            batch_id=data.get("batch_id"),
            from_qty=Decimal(str(data["from_qty"])),
            from_unit=data["from_unit"],
            to_qty=Decimal(str(data["to_qty"])),
            to_unit=data["to_unit"],
            conversion_ratio=Decimal(str(data["conversion_ratio"])),
            detail=data.get("detail"),
            transfer_date=data.get("transfer_date", date.today()),
            status=StockStatus.PENDING,
            notes=data.get("notes"),
        )
        db.add(transfer)
        await db.commit()
        await db.refresh(transfer)
        return transfer

    @staticmethod
    async def confirm_transfer(db: AsyncSession, transfer: StockTransfer) -> tuple[Stock, Stock]:
        if transfer.status != StockStatus.PENDING:
            raise ValueError("只有待确认的调拨单可以确认")

        from_stock = await WarehouseV2Service.get_or_create_stock(
            db, transfer.from_warehouse_id, transfer.product_id, transfer.batch_id, transfer.from_unit
        )
        if from_stock.available_qty < transfer.from_qty:
            raise ValueError(f"调出仓库存不足：可用{from_stock.available_qty}，需要{transfer.from_qty}")

        from_qty_before = from_stock.current_qty
        from_stock.current_qty = (from_stock.current_qty - transfer.from_qty).quantize(Decimal("0.001"))
        from_stock.available_qty = (from_stock.current_qty - from_stock.reserved_qty).quantize(Decimal("0.001"))
        from_stock.last_out_date = transfer.transfer_date

        to_stock = await WarehouseV2Service.get_or_create_stock(
            db, transfer.to_warehouse_id, transfer.product_id, transfer.batch_id, transfer.to_unit
        )
        to_qty_before = to_stock.current_qty
        to_stock.current_qty = (to_stock.current_qty + transfer.to_qty).quantize(Decimal("0.001"))
        to_stock.available_qty = (to_stock.current_qty - to_stock.reserved_qty).quantize(Decimal("0.001"))
        to_stock.last_in_date = transfer.transfer_date

        transfer_cost = transfer.from_qty * (from_stock.unit_cost or Decimal("0"))
        to_unit_cost = transfer_cost / transfer.to_qty if transfer.to_qty > 0 else Decimal("0")

        old_total = to_qty_before * (to_stock.unit_cost or Decimal("0"))
        new_total = transfer.to_qty * to_unit_cost
        if to_stock.current_qty > 0:
            to_stock.unit_cost = ((old_total + new_total) / to_stock.current_qty).quantize(Decimal("0.0001"))
        to_stock.total_cost = (to_stock.current_qty * (to_stock.unit_cost or Decimal("0"))).quantize(Decimal("0.01"))

        transfer.status = StockStatus.COMPLETED
        transfer.confirmed_at = func.now()

        db.add(StockMovement(
            warehouse_id=transfer.from_warehouse_id,
            product_id=transfer.product_id,
            batch_id=transfer.batch_id,
            batch_no=None,
            movement_type=StockMovementType.TRANSFER_OUT,
            movement_date=transfer.transfer_date,
            qty_change=-transfer.from_qty,
            qty_before=from_qty_before,
            qty_after=from_stock.current_qty,
            unit=transfer.from_unit,
            unit_cost=from_stock.unit_cost,
            total_cost=transfer_cost.quantize(Decimal("0.01")),
            ref_type="StockTransfer",
            ref_id=transfer.id,
            ref_no=transfer.transfer_no,
        ))
        db.add(StockMovement(
            warehouse_id=transfer.to_warehouse_id,
            product_id=transfer.product_id,
            batch_id=transfer.batch_id,
            batch_no=None,
            movement_type=StockMovementType.TRANSFER_IN,
            movement_date=transfer.transfer_date,
            qty_change=transfer.to_qty,
            qty_before=to_qty_before,
            qty_after=to_stock.current_qty,
            unit=transfer.to_unit,
            unit_cost=to_unit_cost.quantize(Decimal("0.0001")),
            total_cost=transfer_cost.quantize(Decimal("0.01")),
            ref_type="StockTransfer",
            ref_id=transfer.id,
            ref_no=transfer.transfer_no,
        ))

        await db.commit()
        await db.refresh(from_stock)
        await db.refresh(to_stock)
        return from_stock, to_stock

    @staticmethod
    async def list_transfers(
        db: AsyncSession,
        from_warehouse_id: int | None = None,
        to_warehouse_id: int | None = None,
        product_id: int | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        query = select(StockTransfer, Product).join(
            Product, StockTransfer.product_id == Product.id
        )

        if from_warehouse_id:
            query = query.where(StockTransfer.from_warehouse_id == from_warehouse_id)
        if to_warehouse_id:
            query = query.where(StockTransfer.to_warehouse_id == to_warehouse_id)
        if product_id:
            query = query.where(StockTransfer.product_id == product_id)
        if status:
            query = query.where(StockTransfer.status == status)

        query = query.order_by(desc(StockTransfer.transfer_date))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        items = []
        for transfer, product in rows:
            from_wh = await WarehouseV2Service.get_warehouse(db, transfer.from_warehouse_id)
            to_wh = await WarehouseV2Service.get_warehouse(db, transfer.to_warehouse_id)
            items.append({
                "id": transfer.id,
                "transfer_no": transfer.transfer_no,
                "from_warehouse_id": transfer.from_warehouse_id,
                "from_warehouse_name": from_wh.name if from_wh else None,
                "to_warehouse_id": transfer.to_warehouse_id,
                "to_warehouse_name": to_wh.name if to_wh else None,
                "product_id": transfer.product_id,
                "product_name": product.name,
                "batch_id": transfer.batch_id,
                "from_qty": transfer.from_qty,
                "from_unit": transfer.from_unit,
                "to_qty": transfer.to_qty,
                "to_unit": transfer.to_unit,
                "conversion_ratio": transfer.conversion_ratio,
                "detail": transfer.detail,
                "status": transfer.status.value,
                "transfer_date": transfer.transfer_date,
                "confirmed_at": transfer.confirmed_at,
                "notes": transfer.notes,
                "created_at": transfer.created_at,
                "updated_at": transfer.updated_at,
            })
        return items, total

    @staticmethod
    async def get_transfer(db: AsyncSession, transfer_id: int) -> StockTransfer | None:
        result = await db.execute(select(StockTransfer).where(StockTransfer.id == transfer_id))
        return result.scalar_one_or_none()

    # ==================== 库存变动查询 ====================

    @staticmethod
    async def list_movements(
        db: AsyncSession,
        warehouse_id: int | None = None,
        product_id: int | None = None,
        batch_no: str | None = None,
        movement_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        query = select(StockMovement, Warehouse, Product).join(
            Warehouse, StockMovement.warehouse_id == Warehouse.id
        ).join(Product, StockMovement.product_id == Product.id)

        if warehouse_id:
            query = query.where(StockMovement.warehouse_id == warehouse_id)
        if product_id:
            query = query.where(StockMovement.product_id == product_id)
        if batch_no:
            query = query.where(StockMovement.batch_no == batch_no)
        if movement_type:
            query = query.where(StockMovement.movement_type == movement_type)
        if start_date:
            query = query.where(StockMovement.movement_date >= start_date)
        if end_date:
            query = query.where(StockMovement.movement_date <= end_date)

        query = query.order_by(desc(StockMovement.movement_date), desc(StockMovement.id))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        items = []
        for movement, wh, product in rows:
            items.append({
                "id": movement.id,
                "warehouse_id": movement.warehouse_id,
                "warehouse_name": wh.name,
                "product_id": movement.product_id,
                "product_name": product.name,
                "batch_id": movement.batch_id,
                "batch_no": movement.batch_no,
                "movement_type": movement.movement_type.value,
                "movement_date": movement.movement_date,
                "qty_change": movement.qty_change,
                "qty_before": movement.qty_before,
                "qty_after": movement.qty_after,
                "box_count_change": movement.box_count_change,
                "box_count_before": movement.box_count_before,
                "box_count_after": movement.box_count_after,
                "unit": movement.unit,
                "unit_cost": movement.unit_cost,
                "total_cost": movement.total_cost,
                "ref_type": movement.ref_type,
                "ref_id": movement.ref_id,
                "ref_no": movement.ref_no,
                "notes": movement.notes,
                "created_at": movement.created_at,
                "updated_at": movement.updated_at,
            })
        return items, total

    # ==================== 业务集成 ====================

    @staticmethod
    async def auto_inbound_from_invoice(
        db: AsyncSession,
        invoice_id: int,
        invoice_no: str,
        product_id: int,
        qty: Decimal,
        unit: str,
        unit_cost: Decimal,
        batch_id: int | None = None,
        detail: dict | None = None,
    ) -> StockInbound:
        """进口发票到港 → 自动入库到 ZB-IMPORT"""
        wh = await WarehouseV2Service.get_warehouse_by_code(db, "ZB-IMPORT")
        if not wh:
            raise ValueError("进口整包仓(ZB-IMPORT)不存在，请先初始化仓库")

        inbound_data = {
            "source_type": "import_invoice",
            "source_id": invoice_id,
            "source_no": invoice_no,
            "warehouse_id": wh.id,
            "product_id": product_id,
            "batch_id": batch_id,
            "batch_no": invoice_no,  # 使用发票号作为批次号
            "qty": qty,
            "unit": unit,
            "unit_cost": unit_cost,
            "detail": detail,
            "inbound_date": date.today(),
        }
        inbound = await WarehouseV2Service.create_inbound(db, inbound_data)
        await WarehouseV2Service.confirm_inbound(db, inbound)
        return inbound

    @staticmethod
    async def auto_outbound_from_sale(
        db: AsyncSession,
        sale_id: int,
        sale_no: str,
        warehouse_id: int,
        product_id: int,
        qty: Decimal,
        unit: str,
        batch_id: int | None = None,
    ) -> StockOutbound:
        """销售单创建 → 自动出库"""
        outbound_data = {
            "dest_type": "sale",
            "dest_id": sale_id,
            "dest_no": sale_no,
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "batch_id": batch_id,
            "qty": qty,
            "unit": unit,
            "outbound_date": date.today(),
        }
        outbound = await WarehouseV2Service.create_outbound(db, outbound_data)
        await WarehouseV2Service.confirm_outbound(db, outbound)
        return outbound
