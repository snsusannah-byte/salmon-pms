from typing import List, Optional, Tuple
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FinishedProductSale, SalesStatus, Company, Product, User


class FinishedProductSaleService:
    """成品销售管理服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, sale_id: int) -> Optional[FinishedProductSale]:
        result = await db.execute(select(FinishedProductSale).where(FinishedProductSale.id == sale_id))
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
        query = select(FinishedProductSale)
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
        sale = FinishedProductSale(**data)
        db.add(sale)
        await db.commit()
        await db.refresh(sale)
        return sale

    @staticmethod
    async def update_sale(db: AsyncSession, sale: FinishedProductSale, data: dict) -> FinishedProductSale:
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
    async def delete_sale(db: AsyncSession, sale: FinishedProductSale) -> None:
        if sale.is_locked:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="销售记录已锁定，不能删除")
        await db.delete(sale)
        await db.commit()

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
                func.sum(case((FinishedProductSale.status == SalesStatus.PENDING, 1), else_=0)),
                func.sum(case((FinishedProductSale.status == SalesStatus.PARTIAL_PAID, 1), else_=0)),
                func.sum(case((FinishedProductSale.status == SalesStatus.FULLY_PAID, 1), else_=0)),
            )
        )
        row = result.one()
        total_sales, total_qty, total_gross, total_net, total_paid, pending, partial, fully = row

        return {
            "total_sales": total_sales or 0,
            "total_quantity": total_qty or 0,
            "total_gross_amount": total_gross or Decimal("0"),
            "total_net_amount": total_net or Decimal("0"),
            "total_paid": total_paid or Decimal("0"),
            "total_unpaid": (total_net or Decimal("0")) - (total_paid or Decimal("0")),
            "pending_count": pending or 0,
            "partial_count": partial or 0,
            "fully_paid_count": fully or 0,
        }
