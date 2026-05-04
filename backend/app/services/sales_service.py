from typing import List, Optional, Tuple
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WholeFishSale, SalesReceipt, AftersalesRecord, SalesStatus, Company, Batch, User


class SalesService:
    """销售管理服务"""

    @staticmethod
    async def get_sale_by_id(db: AsyncSession, sale_id: int) -> Optional[WholeFishSale]:
        result = await db.execute(
            select(WholeFishSale)
            .options(
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
        
        query = select(WholeFishSale)
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
        sale = WholeFishSale(**data)
        db.add(sale)
        await db.commit()
        await db.refresh(sale)
        return sale

    @staticmethod
    async def update_sale(db: AsyncSession, sale: WholeFishSale, data: dict) -> WholeFishSale:
        if sale.is_locked:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="销售记录已锁定，不能修改")

        for field, value in data.items():
            if value is not None:
                setattr(sale, field, value)
        await db.commit()
        await db.refresh(sale)
        return sale

    @staticmethod
    async def delete_sale(db: AsyncSession, sale: WholeFishSale) -> None:
        if sale.is_locked:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="销售记录已锁定，不能删除")
        await db.delete(sale)
        await db.commit()

    # ============== 收款记录 ==============

    @staticmethod
    async def add_receipt(db: AsyncSession, sale_id: int, data: dict) -> SalesReceipt:
        sale = await SalesService.get_sale_by_id(db, sale_id)
        if not sale:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="销售记录不存在")
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")

        receipt = SalesReceipt(sale_id=sale_id, **data)
        db.add(receipt)
        await db.commit()
        await db.refresh(receipt)

        # 更新已付金额和状态
        await SalesService._update_paid_amount(db, sale)
        return receipt

    @staticmethod
    async def delete_receipt(db: AsyncSession, receipt_id: int) -> None:
        result = await db.execute(select(SalesReceipt).where(SalesReceipt.id == receipt_id))
        receipt = result.scalar_one_or_none()
        if not receipt:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="收款记录不存在")

        sale = await SalesService.get_sale_by_id(db, receipt.sale_id)
        if sale and sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")

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
