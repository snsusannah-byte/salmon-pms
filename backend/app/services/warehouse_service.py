"""
成品仓库 Service
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finished_product_v2 import (
    WarehousePurchaseOrder,
    WarehouseStock,
)
from app.models import Product, ProductCategory


class WarehouseService:
    """成品仓库服务"""

    # ==================== 采购入库 ====================

    @staticmethod
    async def create_purchase_order(db: AsyncSession, data: dict) -> WarehousePurchaseOrder:
        """创建采购入库单"""
        total_amount = data.get("total_amount")
        if total_amount is None:
            total_amount = (Decimal(str(data["quantity"])) * Decimal(str(data["unit_price"]))).quantize(Decimal("0.01"))
        
        order = WarehousePurchaseOrder(
            order_date=data.get("order_date", date.today()),
            product_id=data["product_id"],
            supplier_id=data.get("supplier_id"),
            batch_no=data.get("batch_no"),
            quantity=Decimal(str(data["quantity"])),
            unit=data.get("unit", "kg"),
            unit_price=Decimal(str(data["unit_price"])),
            total_amount=total_amount,
            lead_time_days=data.get("lead_time_days", 0),
            warehouse_location=data.get("warehouse_location"),
            notes=data.get("notes"),
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        # 自动更新库存
        await WarehouseService._update_stock_on_inbound(db, order)
        
        return order

    @staticmethod
    async def _update_stock_on_inbound(db: AsyncSession, order: WarehousePurchaseOrder):
        """入库后更新库存"""
        result = await db.execute(
            select(WarehouseStock).where(WarehouseStock.product_id == order.product_id)
        )
        stock = result.scalar_one_or_none()
        
        if not stock:
            # 创建新库存记录
            stock = WarehouseStock(
                product_id=order.product_id,
                current_quantity=order.quantity,
                reserved_quantity=Decimal("0"),
                available_quantity=order.quantity,
                unit_cost=order.unit_price,
                last_in_date=order.order_date,
            )
            db.add(stock)
        else:
            # 更新现有库存（加权平均成本）
            old_total_cost = stock.current_quantity * (stock.unit_cost or Decimal("0"))
            new_total_cost = order.quantity * order.unit_price
            total_qty = stock.current_quantity + order.quantity
            
            if total_qty > 0:
                stock.unit_cost = ((old_total_cost + new_total_cost) / total_qty).quantize(Decimal("0.0001"))
            
            stock.current_quantity = total_qty.quantize(Decimal("0.001"))
            stock.available_quantity = (stock.current_quantity - stock.reserved_quantity).quantize(Decimal("0.001"))
            stock.last_in_date = order.order_date
        
        # 更新预警状态
        await WarehouseService._update_warning_status(db, stock)
        await db.commit()

    @staticmethod
    async def list_purchase_orders(
        db: AsyncSession,
        product_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[WarehousePurchaseOrder], int]:
        """采购入库列表"""
        query = select(WarehousePurchaseOrder)
        
        if product_id:
            query = query.where(WarehousePurchaseOrder.product_id == product_id)
        if supplier_id:
            query = query.where(WarehousePurchaseOrder.supplier_id == supplier_id)
        if start_date:
            query = query.where(WarehousePurchaseOrder.order_date >= start_date)
        if end_date:
            query = query.where(WarehousePurchaseOrder.order_date <= end_date)
        
        query = query.order_by(desc(WarehousePurchaseOrder.order_date))
        
        total_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar()
        
        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def get_purchase_order_by_id(db: AsyncSession, order_id: int) -> Optional[WarehousePurchaseOrder]:
        """按ID获取采购单"""
        result = await db.execute(
            select(WarehousePurchaseOrder).where(WarehousePurchaseOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    # ==================== 库存管理 ====================

    @staticmethod
    async def get_or_create_stock(db: AsyncSession, product_id: int) -> WarehouseStock:
        """获取或创建库存记录"""
        result = await db.execute(
            select(WarehouseStock).where(WarehouseStock.product_id == product_id)
        )
        stock = result.scalar_one_or_none()
        
        if not stock:
            stock = WarehouseStock(
                product_id=product_id,
                current_quantity=Decimal("0"),
                reserved_quantity=Decimal("0"),
                available_quantity=Decimal("0"),
            )
            db.add(stock)
            await db.commit()
            await db.refresh(stock)
        
        return stock

    @staticmethod
    async def list_stocks(
        db: AsyncSession,
        category: Optional[str] = None,
        is_below_warning: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[dict], int]:
        """库存列表（含产品信息）"""
        query = select(WarehouseStock, Product).join(
            Product, WarehouseStock.product_id == Product.id
        )
        
        if category:
            query = query.where(Product.category == category)
        if is_below_warning is not None:
            query = query.where(WarehouseStock.is_below_warning == is_below_warning)
        
        total_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar()
        
        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()
        
        items = []
        for stock, product in rows:
            items.append({
                "id": stock.id,
                "product_id": stock.product_id,
                "product_name": product.name,
                "product_category": product.category,
                "product_unit": product.unit,
                "current_quantity": stock.current_quantity,
                "reserved_quantity": stock.reserved_quantity,
                "available_quantity": stock.available_quantity,
                "unit_cost": stock.unit_cost,
                "warehouse_location": stock.warehouse_location,
                "last_in_date": stock.last_in_date,
                "last_out_date": stock.last_out_date,
                "warning_threshold": stock.warning_threshold,
                "is_below_warning": stock.is_below_warning,
                "lead_time_days": product.lead_time_days or 0,
                "avg_daily_consumption": product.avg_daily_consumption or Decimal("0"),
                "safety_buffer": product.safety_buffer or 0,
                "notes": stock.notes,
                "created_at": stock.created_at,
                "updated_at": stock.updated_at,
            })
        
        return items, total

    @staticmethod
    async def get_stock_by_product(db: AsyncSession, product_id: int) -> Optional[dict]:
        """按产品获取库存"""
        result = await db.execute(
            select(WarehouseStock, Product)
            .join(Product, WarehouseStock.product_id == Product.id)
            .where(WarehouseStock.product_id == product_id)
        )
        row = result.one_or_none()
        if not row:
            return None
        
        stock, product = row
        return {
            "id": stock.id,
            "product_id": stock.product_id,
            "product_name": product.name,
            "product_category": product.category,
            "current_quantity": stock.current_quantity,
            "available_quantity": stock.available_quantity,
            "unit_cost": stock.unit_cost,
        }

    @staticmethod
    async def stock_out(
        db: AsyncSession,
        product_id: int,
        quantity: Decimal,
        reason: str = "sale",
    ) -> WarehouseStock:
        """出库（销售时调用）"""
        stock = await WarehouseService.get_or_create_stock(db, product_id)
        
        if stock.available_quantity < quantity:
            raise ValueError(f"库存不足：可用{stock.available_quantity}，需要{quantity}")
        
        stock.current_quantity = (stock.current_quantity - quantity).quantize(Decimal("0.001"))
        stock.available_quantity = (stock.current_quantity - stock.reserved_quantity).quantize(Decimal("0.001"))
        stock.last_out_date = date.today()
        
        # 更新预警
        await WarehouseService._update_warning_status(db, stock)
        await db.commit()
        await db.refresh(stock)
        
        return stock

    @staticmethod
    async def stock_in(
        db: AsyncSession,
        product_id: int,
        quantity: Decimal,
        unit_price: Optional[Decimal] = None,
        reason: str = "manual",
    ) -> WarehouseStock:
        """直接入库（无采购单）"""
        stock = await WarehouseService.get_or_create_stock(db, product_id)
        
        stock.current_quantity = (stock.current_quantity + quantity).quantize(Decimal("0.001"))
        stock.available_quantity = (stock.current_quantity - stock.reserved_quantity).quantize(Decimal("0.001"))
        stock.last_in_date = date.today()
        
        if unit_price:
            # 加权平均
            old_cost = (stock.current_quantity - quantity) * (stock.unit_cost or Decimal("0"))
            new_cost = quantity * unit_price
            if stock.current_quantity > 0:
                stock.unit_cost = ((old_cost + new_cost) / stock.current_quantity).quantize(Decimal("0.0001"))
        
        await WarehouseService._update_warning_status(db, stock)
        await db.commit()
        await db.refresh(stock)
        
        return stock

    @staticmethod
    async def _update_warning_status(db: AsyncSession, stock: WarehouseStock):
        """更新库存预警状态"""
        # 获取产品信息
        result = await db.execute(
            select(Product).where(Product.id == stock.product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            return
        
        # 计算预警线 = 供货周期 × 日均消耗 + 安全缓冲
        lead_time = product.lead_time_days or 0
        avg_daily = product.avg_daily_consumption or Decimal("0")
        safety = product.safety_buffer or 0
        
        # 对于副产品，不做预警
        if product.category == ProductCategory.BYPRODUCT.value:
            stock.warning_threshold = 0
            stock.is_below_warning = False
            return
        
        # 计算预警阈值
        threshold = int(lead_time * float(avg_daily) + safety)
        stock.warning_threshold = threshold
        
        # 判断是否低于预警线
        # 对于按件管理的（包装物、配套），用当前数量对比
        # 对于按重量管理的（整鱼、鱼柳），用当前重量对比
        if threshold > 0:
            stock.is_below_warning = float(stock.available_quantity) < threshold
        else:
            stock.is_below_warning = False

    @staticmethod
    async def get_warning_list(db: AsyncSession) -> List[dict]:
        """获取库存预警列表"""
        result = await db.execute(
            select(WarehouseStock, Product)
            .join(Product, WarehouseStock.product_id == Product.id)
            .where(WarehouseStock.is_below_warning)
            .where(Product.category != ProductCategory.BYPRODUCT)  # 副产品不预警
        )
        
        rows = result.all()
        items = []
        for stock, product in rows:
            threshold = stock.warning_threshold or 0
            shortage = Decimal(str(threshold)) - stock.available_quantity
            if shortage < 0:
                shortage = Decimal("0")
            
            items.append({
                "product_id": stock.product_id,
                "product_name": product.name,
                "product_category": product.category,
                "current_quantity": stock.available_quantity,
                "warning_threshold": threshold,
                "shortage": shortage.quantize(Decimal("0.001")),
                "lead_time_days": product.lead_time_days or 0,
                "avg_daily_consumption": product.avg_daily_consumption or Decimal("0"),
                "safety_buffer": product.safety_buffer or 0,
            })
        
        return items

    @staticmethod
    async def update_daily_consumption(db: AsyncSession, product_id: int, days: int = 30):
        """根据历史销量更新日均消耗（预警线计算用）"""
        # 查询最近N天的出库总量
        from_date = date.today() - timedelta(days=days)
        
        result = await db.execute(
            select(func.sum(WarehousePurchaseOrder.quantity))
            .where(WarehousePurchaseOrder.product_id == product_id)
            .where(WarehousePurchaseOrder.order_date >= from_date)
        )
        total_qty = result.scalar() or Decimal("0")
        
        avg_daily = Decimal("0")
        if days > 0:
            avg_daily = (total_qty / Decimal(str(days))).quantize(Decimal("0.0001"))
        
        # 更新产品表的日均消耗
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if product:
            product.avg_daily_consumption = avg_daily
            await db.commit()
        
        return avg_daily

    @staticmethod
    async def delete_purchase_order(db: AsyncSession, order: WarehousePurchaseOrder):
        """删除采购入库单（同时回滚库存）"""
        # 回滚库存
        stock = await WarehouseService.get_or_create_stock(db, order.product_id)
        
        stock.current_quantity = (stock.current_quantity - order.quantity).quantize(Decimal("0.001"))
        if stock.current_quantity < 0:
            stock.current_quantity = Decimal("0")
        stock.available_quantity = (stock.current_quantity - stock.reserved_quantity).quantize(Decimal("0.001"))
        if stock.available_quantity < 0:
            stock.available_quantity = Decimal("0")
        
        await WarehouseService._update_warning_status(db, stock)
        
        await db.delete(order)
        await db.commit()
