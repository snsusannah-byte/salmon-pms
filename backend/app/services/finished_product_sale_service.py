from typing import List, Optional, Tuple
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    FinishedProductSale,
    FinishedProductReceipt,
    FinishedProductAftersales,
    SalesStatus,
    Company,
    Product,
    ProductCategory,
    ProductPackaging,
    WarehouseStock,
)


class FinishedProductSaleService:
    """成品销售管理服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, sale_id: int) -> Optional[FinishedProductSale]:
        result = await db.execute(
            select(FinishedProductSale)
            .options(
                selectinload(FinishedProductSale.receipts),
                selectinload(FinishedProductSale.aftersales_records),
            )
            .where(FinishedProductSale.id == sale_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_sales(
        db: AsyncSession,
        customer_id: Optional[int] = None,
        product_id: Optional[int] = None,
        status: Optional[SalesStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[FinishedProductSale], int]:
        query = select(FinishedProductSale).options(
            selectinload(FinishedProductSale.receipts),
            selectinload(FinishedProductSale.aftersales_records),
        )
        count_query = select(func.count(FinishedProductSale.id))

        filters = []
        if customer_id:
            filters.append(FinishedProductSale.customer_id == customer_id)
        if product_id:
            filters.append(FinishedProductSale.product_id == product_id)
        if status:
            filters.append(FinishedProductSale.status == status)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        query = query.order_by(FinishedProductSale.sale_date.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return list(items), total

    @staticmethod
    async def create_sale(db: AsyncSession, data: dict) -> FinishedProductSale:
        # V3: 自动计算总重量（份数 × 每份重量(g) / 1000）
        if data.get("product_id") and data.get("quantity"):
            result = await db.execute(
                select(Product.portion_weight_g).where(Product.id == data["product_id"])
            )
            portion_weight_g = result.scalar()
            if portion_weight_g:
                data["total_weight_kg"] = Decimal(data["quantity"]) * Decimal(portion_weight_g) / Decimal("1000")
        
        sale = FinishedProductSale(**data)
        db.add(sale)
        await db.commit()
        await db.refresh(sale)
        
        # V3: 扣减库存（成品 + 包装物料 + 配套）
        await FinishedProductSaleService._deduct_stock(db, sale)
        
        return sale

    @staticmethod
    async def update_sale(
        db: AsyncSession, sale: FinishedProductSale, data: dict
    ) -> FinishedProductSale:
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定，不能修改")

        # V3: 如果更新了产品或份数，需要调整库存
        need_stock_update = (
            "product_id" in data or 
            "quantity" in data or 
            "total_weight_kg" in data
        )
        
        if need_stock_update:
            # 先恢复旧库存
            await FinishedProductSaleService._restore_stock(db, sale)
        
        # V3: 如果更新了产品或份数，重新计算总重量
        product_id = data.get("product_id", sale.product_id)
        quantity = data.get("quantity", sale.quantity)
        if "product_id" in data or "quantity" in data:
            from app.models import Product
            result = await db.execute(
                select(Product.portion_weight_g).where(Product.id == product_id)
            )
            portion_weight_g = result.scalar()
            if portion_weight_g:
                data["total_weight_kg"] = Decimal(quantity) * Decimal(portion_weight_g) / Decimal("1000")

        for field, value in data.items():
            if value is not None:
                setattr(sale, field, value)
        await db.commit()
        await db.refresh(sale)
        
        # V3: 扣减新库存
        if need_stock_update:
            await FinishedProductSaleService._deduct_stock(db, sale)
        
        return sale

    @staticmethod
    async def delete_sale(db: AsyncSession, sale: FinishedProductSale) -> None:
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定，不能删除")
        
        # V3: 恢复库存
        await FinishedProductSaleService._restore_stock(db, sale)
        
        await db.delete(sale)
        await db.commit()

    # ============== 库存扣减 ==============

    @staticmethod
    async def _deduct_stock(db: AsyncSession, sale: FinishedProductSale) -> None:
        """销售时扣减库存：成品 + 包装物料 + 配套产品
        
        1. 成品肉：扣减重量(kg) = 份数 × 每份重量(g) / 1000
        2. 配套产品：根据 product_accessories 配置扣减
        3. 包装物料：根据 product_packagings 配置扣减
        """
        from sqlalchemy.orm import selectinload
        from app.models.finished_product_v2 import WarehouseStock
        from app.models import ProductAccessory
        
        quantity = Decimal(str(sale.quantity))
        product_id = sale.product_id
        sale_date = sale.sale_date
        
        # 1. 扣减成品肉库存（按重量kg）
        if sale.total_weight_kg:
            await FinishedProductSaleService._deduct_product_stock(
                db, product_id, sale.total_weight_kg, sale_date
            )
        
        # 2. 扣减配套产品库存
        result = await db.execute(
            select(ProductAccessory)
            .options(selectinload(ProductAccessory.accessory))
            .where(ProductAccessory.product_id == product_id)
        )
        accessories = result.scalars().all()
        
        for acc in accessories:
            total_qty = acc.quantity * quantity
            await FinishedProductSaleService._deduct_product_stock(
                db, acc.accessory_id, total_qty, sale_date
            )
        
        # 3. 扣减包装物料库存
        result = await db.execute(
            select(ProductPackaging)
            .options(selectinload(ProductPackaging.material))
            .where(ProductPackaging.product_id == product_id)
        )
        packagings = result.scalars().all()
        
        for pkg in packagings:
            total_qty = pkg.quantity * quantity
            await FinishedProductSaleService._deduct_product_stock(
                db, pkg.material_id, total_qty, sale_date
            )
        
        await db.commit()

    @staticmethod
    async def _deduct_product_stock(
        db: AsyncSession, 
        product_id: int, 
        quantity: Decimal,
        sale_date: date
    ) -> None:
        """扣减单个产品的库存"""
        from app.models.finished_product_v2 import WarehouseStock
        
        result = await db.execute(
            select(WarehouseStock).where(WarehouseStock.product_id == product_id)
        )
        stock = result.scalar_one_or_none()
        
        if stock:
            # 扣减库存
            stock.current_quantity -= quantity
            stock.available_quantity = stock.current_quantity - stock.reserved_quantity
            stock.last_out_date = sale_date
            
            # 检查预警
            if stock.warning_threshold > 0 and stock.available_quantity < stock.warning_threshold:
                stock.is_below_warning = True
            else:
                stock.is_below_warning = False
            
            db.add(stock)
        else:
            # 如果没有库存记录，创建一个（允许负库存）
            new_stock = WarehouseStock(
                product_id=product_id,
                current_quantity=-quantity,
                available_quantity=-quantity,
                reserved_quantity=Decimal("0"),
                last_out_date=sale_date,
            )
            db.add(new_stock)

    @staticmethod
    async def _restore_stock(db: AsyncSession, sale: FinishedProductSale) -> None:
        """删除销售时恢复库存"""
        from app.models.finished_product_v2 import WarehouseStock
        from sqlalchemy.orm import selectinload
        from app.models import ProductAccessory
        
        quantity = Decimal(str(sale.quantity))
        product_id = sale.product_id
        
        # 1. 恢复成品肉库存
        if sale.total_weight_kg:
            await FinishedProductSaleService._restore_product_stock(
                db, product_id, sale.total_weight_kg
            )
        
        # 2. 恢复配套产品库存
        result = await db.execute(
            select(ProductAccessory)
            .options(selectinload(ProductAccessory.accessory))
            .where(ProductAccessory.product_id == product_id)
        )
        accessories = result.scalars().all()
        
        for acc in accessories:
            total_qty = acc.quantity * quantity
            await FinishedProductSaleService._restore_product_stock(
                db, acc.accessory_id, total_qty
            )
        
        # 3. 恢复包装物料库存
        result = await db.execute(
            select(ProductPackaging)
            .options(selectinload(ProductPackaging.material))
            .where(ProductPackaging.product_id == product_id)
        )
        packagings = result.scalars().all()
        
        for pkg in packagings:
            total_qty = pkg.quantity * quantity
            await FinishedProductSaleService._restore_product_stock(
                db, pkg.material_id, total_qty
            )
        
        await db.commit()

    @staticmethod
    async def _restore_product_stock(db: AsyncSession, product_id: int, quantity: Decimal) -> None:
        """恢复单个产品的库存"""
        from app.models.finished_product_v2 import WarehouseStock
        
        result = await db.execute(
            select(WarehouseStock).where(WarehouseStock.product_id == product_id)
        )
        stock = result.scalar_one_or_none()
        
        if stock:
            stock.current_quantity += quantity
            stock.available_quantity = stock.current_quantity - stock.reserved_quantity
            
            if stock.warning_threshold > 0 and stock.available_quantity >= stock.warning_threshold:
                stock.is_below_warning = False
            
            db.add(stock)

    @staticmethod
    async def _update_stock_on_sale_change(
        db: AsyncSession, 
        old_sale: FinishedProductSale, 
        new_data: dict
    ) -> None:
        """更新销售时调整库存（先恢复旧库存，再扣减新库存）"""
        # 恢复旧库存
        await FinishedProductSaleService._restore_stock(db, old_sale)
        
        # 更新 old_sale 的字段以便扣减新库存
        for field, value in new_data.items():
            if value is not None and field != "id":
                setattr(old_sale, field, value)
        
        # 重新计算总重量
        if new_data.get("quantity") and new_data.get("product_id"):
            result = await db.execute(
                select(Product.portion_weight_g)
                .where(Product.id == new_data["product_id"])
            )
            portion_weight_g = result.scalar()
            if portion_weight_g:
                old_sale.total_weight_kg = Decimal(new_data["quantity"]) * Decimal(portion_weight_g) / Decimal("1000")
        
        # 扣减新库存
        await FinishedProductSaleService._deduct_stock(db, old_sale)

    # ============== 收款记录 ==============

    @staticmethod
    async def add_receipt(
        db: AsyncSession, sale_id: int, data: dict
    ) -> FinishedProductReceipt:
        sale = await FinishedProductSaleService.get_by_id(db, sale_id)
        if not sale:
            raise HTTPException(status_code=404, detail="销售记录不存在")
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")

        receipt = FinishedProductReceipt(sale_id=sale_id, **data)
        db.add(receipt)
        await db.commit()
        await db.refresh(receipt)

        # 更新已付金额和状态
        await FinishedProductSaleService._update_paid_amount(db, sale)
        return receipt

    @staticmethod
    async def delete_receipt(db: AsyncSession, receipt_id: int) -> None:
        result = await db.execute(
            select(FinishedProductReceipt).where(FinishedProductReceipt.id == receipt_id)
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            raise HTTPException(status_code=404, detail="收款记录不存在")

        sale = await FinishedProductSaleService.get_by_id(db, receipt.sale_id)
        if sale and sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")

        await db.delete(receipt)
        await db.commit()

        if sale:
            await FinishedProductSaleService._update_paid_amount(db, sale)

    @staticmethod
    async def _update_paid_amount(
        db: AsyncSession, sale: FinishedProductSale
    ) -> None:
        result = await db.execute(
            select(func.sum(FinishedProductReceipt.amount)).where(
                FinishedProductReceipt.sale_id == sale.id
            )
        )
        total_paid = result.scalar() or Decimal("0")
        sale.paid_amount = total_paid

        # 更新状态
        if sale.paid_amount >= sale.net_amount:
            sale.status = SalesStatus.FULLY_PAID
        elif sale.paid_amount > 0:
            sale.status = SalesStatus.PARTIAL_PAID
        else:
            sale.status = SalesStatus.PENDING

        await db.commit()

    # ============== 售后记录 ==============

    @staticmethod
    async def add_aftersales(
        db: AsyncSession, sale_id: int, data: dict
    ) -> FinishedProductAftersales:
        sale = await FinishedProductSaleService.get_by_id(db, sale_id)
        if not sale:
            raise HTTPException(status_code=404, detail="销售记录不存在")

        record = FinishedProductAftersales(sale_id=sale_id, **data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_aftersales(
        db: AsyncSession, record: FinishedProductAftersales, data: dict
    ) -> FinishedProductAftersales:
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_aftersales(db: AsyncSession, record_id: int) -> None:
        result = await db.execute(
            select(FinishedProductAftersales).where(
                FinishedProductAftersales.id == record_id
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="售后记录不存在")
        await db.delete(record)
        await db.commit()

    # ============== 信用额度检查 ==============

    @staticmethod
    async def check_customer_credit(
        db: AsyncSession, customer_id: int, new_sale_amount: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """检查客户信用额度

        Returns:
            (is_allowed, message) - 是否允许交易，如不允许返回原因
        """
        result = await db.execute(
            select(Company.credit_limit).where(Company.id == customer_id)
        )
        credit_limit = result.scalar()
        if credit_limit is None:
            credit_limit = Decimal("0")

        # 计算客户当前未付总额
        result = await db.execute(
            select(func.sum(FinishedProductSale.net_amount - FinishedProductSale.paid_amount))
            .where(FinishedProductSale.customer_id == customer_id)
            .where(FinishedProductSale.status.in_([SalesStatus.PENDING, SalesStatus.PARTIAL_PAID]))
        )
        total_unpaid = result.scalar() or Decimal("0")

        # 预估新未付总额 = 当前未付 + 新销售金额
        estimated_unpaid = total_unpaid + new_sale_amount

        if credit_limit > 0 and estimated_unpaid > credit_limit:
            return (
                False,
                f"客户未付金额 ¥{total_unpaid} + 本次 ¥{new_sale_amount} = ¥{estimated_unpaid}，"
                f"超出信用额度 ¥{credit_limit}",
            )

        return True, None

    # ============== 汇总 ==============

    @staticmethod
    async def get_summary(db: AsyncSession) -> dict:
        from sqlalchemy import case

        result = await db.execute(
            select(
                func.count(FinishedProductSale.id),
                func.sum(FinishedProductSale.quantity),
                func.sum(FinishedProductSale.gross_amount),
                func.sum(FinishedProductSale.net_amount),
                func.sum(FinishedProductSale.paid_amount),
                func.sum(FinishedProductSale.total_weight_kg),  # V3: 新增总重量
                func.sum(
                    case(
                        (FinishedProductSale.status == SalesStatus.PENDING, 1), else_=0
                    )
                ),
                func.sum(
                    case(
                        (FinishedProductSale.status == SalesStatus.PARTIAL_PAID, 1),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (FinishedProductSale.status == SalesStatus.FULLY_PAID, 1),
                        else_=0,
                    )
                ),
            )
        )
        row = result.one()
        (
            total_sales,
            total_qty,
            total_gross,
            total_net,
            total_paid,
            total_weight,
            pending,
            partial,
            fully,
        ) = row

        return {
            "total_sales": total_sales or 0,
            "total_quantity": total_qty or 0,
            "total_gross_amount": total_gross or Decimal("0"),
            "total_net_amount": total_net or Decimal("0"),
            "total_paid": total_paid or Decimal("0"),
            "total_unpaid": (total_net or Decimal("0")) - (total_paid or Decimal("0")),
            "total_weight_kg": total_weight or Decimal("0"),  # V3: 新增
            "pending_count": pending or 0,
            "partial_count": partial or 0,
            "fully_paid_count": fully or 0,
        }
