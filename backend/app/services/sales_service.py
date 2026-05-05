from typing import List, Optional, Tuple
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WholeFishSale, WholeFishSaleItem, SalesReceipt, AftersalesRecord, SalesStatus, Company, Batch, User


class SalesService:
    """销售管理服务"""

    @staticmethod
    async def get_sale_by_id(db: AsyncSession, sale_id: int) -> Optional[WholeFishSale]:
        result = await db.execute(
            select(WholeFishSale)
            .options(
                selectinload(WholeFishSale.items),
                selectinload(WholeFishSale.receipts),
                selectinload(WholeFishSale.aftersales),
            )
            .where(WholeFishSale.id == sale_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_sales(
        db: AsyncSession,
        batch_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        status: Optional[SalesStatus] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[WholeFishSale], int]:
        from sqlalchemy import or_
        from app.models import Company, Batch
        
        query = select(WholeFishSale).options(
            selectinload(WholeFishSale.items),
            selectinload(WholeFishSale.receipts),
            selectinload(WholeFishSale.aftersales),
        )
        count_query = select(func.count(WholeFishSale.id))

        filters = []
        if batch_id:
            filters.append(WholeFishSale.batch_id == batch_id)
        if customer_id:
            filters.append(WholeFishSale.customer_id == customer_id)
        if status:
            filters.append(WholeFishSale.status == status)

        if search:
            search_filter = or_(
                Company.name.ilike(f"%{search}%"),
                Batch.batch_name.ilike(f"%{search}%"),
                Batch.batch_code.ilike(f"%{search}%"),
                WholeFishSale.sale_no.ilike(f"%{search}%"),
            )
            filters.append(search_filter)
            query = query.join(Company, WholeFishSale.customer_id == Company.id, isouter=True).join(Batch, WholeFishSale.batch_id == Batch.id, isouter=True)
            count_query = count_query.join(Company, WholeFishSale.customer_id == Company.id, isouter=True).join(Batch, WholeFishSale.batch_id == Batch.id, isouter=True)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        query = query.order_by(WholeFishSale.sale_date.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return list(items), total

    @staticmethod
    async def create_sale(db: AsyncSession, data: dict) -> WholeFishSale:
        # 提取 items 数据
        items_data = data.pop("items", None)
        
        # 如果没有提供主表的 spec/box_count，从 items 第一个取
        if items_data:
            first_item = items_data[0] if isinstance(items_data, list) and len(items_data) > 0 else None
            if first_item:
                if not data.get("spec") and first_item.get("spec"):
                    data["spec"] = first_item.get("spec")
                if not data.get("box_count") and first_item.get("box_count"):
                    data["box_count"] = first_item.get("box_count")
            
            # 从 items 计算总重量和总金额
            total_weight = sum(
                Decimal(str(item.get("weight_kg", 0))) for item in items_data
            )
            total_box_count = sum(
                int(item.get("box_count", 0) or 0) for item in items_data
            )
            total_amount = sum(
                Decimal(str(item.get("weight_kg", 0))) * Decimal(str(item.get("unit_price", 0)))
                for item in items_data
            )
            
            # 如果有 items，用 items 的汇总覆盖主表数据
            if total_weight > 0:
                data["weight_kg"] = total_weight
                data["gross_amount"] = total_amount
                data["net_amount"] = total_amount
                if not data.get("box_count") or total_box_count > 0:
                    data["box_count"] = total_box_count
                # 加权平均单价
                if total_weight > 0:
                    data["unit_price"] = total_amount / total_weight
        
        sale = WholeFishSale(**data)
        db.add(sale)
        await db.flush()  # 获取 sale.id
        
        # 创建子项
        if items_data:
            for idx, item_data in enumerate(items_data):
                item = WholeFishSaleItem(
                    sale_id=sale.id,
                    spec=item_data.get("spec", ""),
                    box_count=item_data.get("box_count", 0) or 0,
                    weight_kg=Decimal(str(item_data.get("weight_kg", 0))),
                    unit_price=Decimal(str(item_data.get("unit_price", 0))),
                    amount=Decimal(str(item_data.get("weight_kg", 0))) * Decimal(str(item_data.get("unit_price", 0))),
                    sort_order=idx,
                    notes=item_data.get("notes"),
                )
                db.add(item)
        
        await db.commit()
        await db.refresh(sale)
        return sale

    @staticmethod
    async def update_sale(db: AsyncSession, sale: WholeFishSale, data: dict) -> WholeFishSale:
        from fastapi import HTTPException
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定，不能修改")
        
        # 提取 items 数据
        items_data = data.pop("items", None)

        # 更新主表字段
        for field, value in data.items():
            if value is not None:
                setattr(sale, field, value)
        
        # 如果提供了 items，替换子项
        if items_data is not None:
            # 删除旧子项
            await db.execute(
                select(WholeFishSaleItem).where(WholeFishSaleItem.sale_id == sale.id)
            )
            # 重新从数据库加载旧子项并删除
            result = await db.execute(
                select(WholeFishSaleItem).where(WholeFishSaleItem.sale_id == sale.id)
            )
            old_items = result.scalars().all()
            for old_item in old_items:
                await db.delete(old_item)
            
            # 创建新子项
            total_weight = Decimal("0")
            total_amount = Decimal("0")
            total_box_count = 0
            for idx, item_data in enumerate(items_data):
                item = WholeFishSaleItem(
                    sale_id=sale.id,
                    spec=item_data.get("spec", ""),
                    box_count=item_data.get("box_count", 0) or 0,
                    weight_kg=Decimal(str(item_data.get("weight_kg", 0))),
                    unit_price=Decimal(str(item_data.get("unit_price", 0))),
                    amount=Decimal(str(item_data.get("weight_kg", 0))) * Decimal(str(item_data.get("unit_price", 0))),
                    sort_order=idx,
                    notes=item_data.get("notes"),
                )
                db.add(item)
                total_weight += item.weight_kg
                total_amount += item.amount
                total_box_count += item.box_count
            
            # 更新主表汇总数据
            if total_weight > 0:
                sale.weight_kg = total_weight
                sale.gross_amount = total_amount
                sale.net_amount = total_amount
                sale.box_count = total_box_count
                sale.unit_price = total_amount / total_weight
        
        await db.commit()
        await db.refresh(sale)
        return sale

    @staticmethod
    async def delete_sale(db: AsyncSession, sale: WholeFishSale) -> None:
        from fastapi import HTTPException
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定，不能删除")
        await db.delete(sale)
        await db.commit()

    # ============== 收款记录 ==============

    @staticmethod
    async def add_receipt(db: AsyncSession, sale_id: int, data: dict) -> SalesReceipt:
        from app.models import TransactionRecord, TransactionType, TransactionCategory, Company
        sale = await SalesService.get_sale_by_id(db, sale_id)
        if not sale:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="销售记录不存在")
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")

        receipt = SalesReceipt(sale_id=sale_id, **data)
        db.add(receipt)
        await db.flush()  # 获取 receipt.id

        # 同步创建交易流水
        # 获取客户名称
        customer_name = None
        if sale.customer_id:
            result = await db.execute(
                select(Company.name).where(Company.id == sale.customer_id)
            )
            customer_name = result.scalar()
        
        bank_account_id = data.get("bank_account_id")
        
        transaction = TransactionRecord(
            transaction_date=data.get("receipt_date"),
            type=TransactionType.INCOME,
            category=TransactionCategory.SALES_INCOME,
            amount=data.get("amount"),
            currency="USD",
            to_account_id=bank_account_id,
            counterparty_id=sale.customer_id,
            counterparty_name=customer_name,
            reference_no=data.get("reference_no") or sale.sale_no or f"#{sale.id}",
            description=f"销售收款: {sale.sale_no or f'#{sale.id}'}",
            notes=data.get("notes"),
            is_confirmed=True,
        )
        db.add(transaction)
        await db.flush()
        
        # 关联交易流水到收款记录
        receipt.transaction_id = transaction.id
        
        await db.commit()
        await db.refresh(receipt)
        await db.refresh(transaction)

        # 更新已付金额和状态
        await SalesService._update_paid_amount(db, sale)
        return receipt

    @staticmethod
    async def delete_receipt(db: AsyncSession, receipt_id: int) -> None:
        from app.models import TransactionRecord
        result = await db.execute(select(SalesReceipt).where(SalesReceipt.id == receipt_id))
        receipt = result.scalar_one_or_none()
        if not receipt:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="收款记录不存在")

        sale = await SalesService.get_sale_by_id(db, receipt.sale_id)
        if sale and sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")
        
        # 同步删除关联的交易流水
        if receipt.transaction_id:
            trans_result = await db.execute(
                select(TransactionRecord).where(TransactionRecord.id == receipt.transaction_id)
            )
            transaction = trans_result.scalar_one_or_none()
            if transaction:
                await db.delete(transaction)

        await db.delete(receipt)
        await db.commit()

        if sale:
            await SalesService._update_paid_amount(db, sale)

    @staticmethod
    async def _update_paid_amount(db: AsyncSession, sale: WholeFishSale) -> None:
        result = await db.execute(
            select(func.sum(SalesReceipt.amount)).where(SalesReceipt.sale_id == sale.id)
        )
        total_paid = result.scalar() or Decimal("0")
        sale.paid_amount = total_paid

        # 重新计算净金额（确保和各调整项一致）
        sale.net_amount = max(
            Decimal("0"),
            sale.gross_amount
            - (sale.scan_fee or Decimal("0"))
            - (sale.rounding_adjustment or Decimal("0"))
            - (sale.after_sales_adjustment or Decimal("0"))
            - (sale.discount or Decimal("0"))
            - (sale.commission or Decimal("0"))
        )

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
    async def add_aftersales(db: AsyncSession, sale_id: int, data: dict) -> AftersalesRecord:
        sale = await SalesService.get_sale_by_id(db, sale_id)
        if not sale:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="销售记录不存在")

        record = AftersalesRecord(sale_id=sale_id, **data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_aftersales(db: AsyncSession, record: AftersalesRecord, data: dict) -> AftersalesRecord:
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_aftersales(db: AsyncSession, record_id: int) -> None:
        result = await db.execute(select(AftersalesRecord).where(AftersalesRecord.id == record_id))
        record = result.scalar_one_or_none()
        if not record:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="售后记录不存在")
        await db.delete(record)
        await db.commit()

    # ============== 汇总 ==============

    @staticmethod
    async def get_summary(db: AsyncSession) -> dict:
        result = await db.execute(
            select(
                func.count(WholeFishSale.id),
                func.sum(WholeFishSale.weight_kg),
                func.sum(WholeFishSale.gross_amount),
                func.sum(WholeFishSale.net_amount),
                func.sum(WholeFishSale.paid_amount),
                func.sum(func.case((WholeFishSale.status == SalesStatus.PENDING, 1), else_=0)),
                func.sum(func.case((WholeFishSale.status == SalesStatus.PARTIAL_PAID, 1), else_=0)),
                func.sum(func.case((WholeFishSale.status == SalesStatus.FULLY_PAID, 1), else_=0)),
            )
        )
        row = result.one()
        total_sales, total_weight, total_gross, total_net, total_paid, pending, partial, fully = row

        return {
            "total_sales": total_sales or 0,
            "total_weight_kg": total_weight or Decimal("0"),
            "total_gross_amount": total_gross or Decimal("0"),
            "total_net_amount": total_net or Decimal("0"),
            "total_paid": total_paid or Decimal("0"),
            "total_unpaid": (total_net or Decimal("0")) - (total_paid or Decimal("0")),
            "pending_count": pending or 0,
            "partial_count": partial or 0,
            "fully_paid_count": fully or 0,
        }
