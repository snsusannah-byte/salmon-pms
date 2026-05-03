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
        sale = FinishedProductSale(**data)
        db.add(sale)
        await db.commit()
        await db.refresh(sale)
        return sale

    @staticmethod
    async def update_sale(
        db: AsyncSession, sale: FinishedProductSale, data: dict
    ) -> FinishedProductSale:
        if sale.is_locked:
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
            raise HTTPException(status_code=400, detail="销售记录已锁定，不能删除")
        await db.delete(sale)
        await db.commit()

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
            "pending_count": pending or 0,
            "partial_count": partial or 0,
            "fully_paid_count": fully or 0,
        }
