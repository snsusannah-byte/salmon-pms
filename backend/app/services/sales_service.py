from typing import List, Optional, Tuple
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WholeFishSale, WholeFishSaleItem, SalesReceipt, AftersalesRecord, SalesStatus, Company, Batch


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
        ids: Optional[List[int]] = None,
        status: Optional[SalesStatus] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[WholeFishSale], int]:
        from sqlalchemy import or_
        
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
        if ids:
            filters.append(WholeFishSale.id.in_(ids))
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

        query = query.order_by(WholeFishSale.sale_date.desc(), WholeFishSale.id.desc())
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
        
        # 自动生成提成记录
        await SalesService._sync_commission_record(db, sale)
        
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

        # 日期字段需要正确转换
        if "sale_date" in data and isinstance(data["sale_date"], str):
            from datetime import date
            data["sale_date"] = date.fromisoformat(data["sale_date"])

        # 更新主表字段
        for field, value in data.items():
            if value is not None or field == "salesperson_id":
                setattr(sale, field, value)
        
        # 重新计算净金额（调整后）
        def _dec(v):
            return Decimal(str(v)) if v is not None else Decimal("0")
        sale.net_amount = max(
            Decimal("0"),
            _dec(sale.gross_amount)
            - _dec(sale.scan_fee)
            - _dec(sale.rounding_adjustment)
            - _dec(sale.after_sales_adjustment)
            - _dec(sale.discount)
            - _dec(sale.commission)
        )
        
        # 同步更新收款状态
        if Decimal(str(sale.paid_amount or 0)) >= sale.net_amount:
            sale.status = SalesStatus.FULLY_PAID
        elif Decimal(str(sale.paid_amount or 0)) > 0:
            sale.status = SalesStatus.PARTIAL_PAID
        else:
            sale.status = SalesStatus.PENDING
        
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
                sale.box_count = total_box_count
                sale.unit_price = total_amount / total_weight
        
        # 重新计算净金额（确保包含所有调整项）
        def _dec(v):
            return Decimal(str(v)) if v is not None else Decimal("0")
        sale.net_amount = max(
            Decimal("0"),
            _dec(sale.gross_amount)
            - _dec(sale.scan_fee)
            - _dec(sale.rounding_adjustment)
            - _dec(sale.after_sales_adjustment)
            - _dec(sale.discount)
            - _dec(sale.commission)
        )
        
        # 同步更新收款状态
        if Decimal(str(sale.paid_amount or 0)) >= sale.net_amount:
            sale.status = SalesStatus.FULLY_PAID
        elif Decimal(str(sale.paid_amount or 0)) > 0:
            sale.status = SalesStatus.PARTIAL_PAID
        else:
            sale.status = SalesStatus.PENDING
        
        # 同步提成记录
        await SalesService._sync_commission_record(db, sale)
        
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

    @staticmethod
    async def _sync_commission_record(db: AsyncSession, sale: WholeFishSale):
        """同步/更新销售对应的提成记录（按元/kg计算）"""
        from sqlalchemy import delete
        from app.models import CommissionRecord, Salesperson
        
        # 删除旧的提成记录
        await db.execute(
            delete(CommissionRecord).where(CommissionRecord.sale_id == sale.id)
        )
        
        # 如果没有业务员，不生成提成记录
        if not sale.salesperson_id:
            return
        
        # 获取业务员提成单价
        result = await db.execute(select(Salesperson).where(Salesperson.id == sale.salesperson_id))
        sp = result.scalar_one_or_none()
        if not sp or not sp.is_active:
            return
        
        rate = Decimal(str(sp.commission_rate or 0))
        weight = Decimal(str(sale.weight_kg or 0))
        commission_amount = (weight * rate).quantize(Decimal("0.01"))
        
        record = CommissionRecord(
            salesperson_id=sale.salesperson_id,
            sale_id=sale.id,
            sale_date=sale.sale_date if isinstance(sale.sale_date, date) else date.fromisoformat(str(sale.sale_date)),
            sale_amount=sale.net_amount,
            weight_kg=weight,
            commission_rate=rate,
            commission_amount=commission_amount,
            status="pending",
        )
        db.add(record)
        await db.flush()

    # ============== 收款记录 ==============

    @staticmethod
    async def add_receipt(db: AsyncSession, sale_id: int, data: dict) -> SalesReceipt:
        from app.models import TransactionRecord, TransactionType, TransactionCategory
        from fastapi import HTTPException
        sale = await SalesService.get_sale_by_id(db, sale_id)
        if not sale:
            raise HTTPException(status_code=404, detail="销售记录不存在")
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")

        # 获取实收金额
        received_amount = Decimal(str(data.get("amount", 0)))
        if received_amount <= 0:
            raise HTTPException(status_code=400, detail="收款金额必须大于0")

        # 获取用户指定的抹零（默认0）
        user_rounding = Decimal(str(data.pop("rounding_adjustment", 0) or 0))
        if user_rounding > 0:
            sale.rounding_adjustment = user_rounding
            await db.flush()

        # 检查是否还有未付余额（已全额收款后禁止再次收款，但允许本次收款略超应收）
        remaining = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))
        if remaining <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"销售单 {sale.sale_no or f'#{sale.id}'} 已全额收款（净金额 ¥{sale.net_amount}，已收 ¥{sale.paid_amount}），无需再次收款。"
            )
        # 允许实收金额大于未付余额（客户凑整多转场景），不再拦截

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
        
        # 构建描述：只保留类型 + 用户输入的收款描述
        user_notes = data.get("notes")
        desc = "销售收款"
        if user_notes:
            desc = f"{desc} - {user_notes}"
        
        transaction = TransactionRecord(
            transaction_date=data.get("receipt_date"),
            type=TransactionType.INCOME,
            category=TransactionCategory.MAIN_BUSINESS_REVENUE,
            amount=data.get("amount"),
            currency="CNY",
            to_account_id=bank_account_id,
            counterparty_id=sale.customer_id,
            counterparty_name=customer_name,
            reference_no=data.get("reference_no") or sale.sale_no or f"#{sale.id}",
            description=desc,
            notes=user_notes,
            is_confirmed=True,
        )
        # 设置关联销售单（JSON 数组）
        import json
        transaction.related_sale_ids = json.dumps([sale.id])
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
        result = await db.execute(select(SalesReceipt).where(SalesReceipt.id == receipt_id))
        receipt = result.scalar_one_or_none()
        if not receipt:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="收款记录不存在")

        sale = await SalesService.get_sale_by_id(db, receipt.sale_id)
        if sale and sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")

        # 同步删除关联的交易流水（如果存在）
        if receipt.transaction_id:
            from app.models import TransactionRecord
            trans_result = await db.execute(
                select(TransactionRecord).where(TransactionRecord.id == receipt.transaction_id)
            )
            transaction = trans_result.scalar_one_or_none()
            if transaction:
                await db.delete(transaction)

        await db.delete(receipt)
        await db.commit()

        if sale:
            # 更新已付金额和状态
            await SalesService._update_paid_amount(db, sale)
            
            # 如果收款全部删除，同步清零因收款产生的抹零
            if Decimal(str(sale.paid_amount or 0)) == 0 and Decimal(str(sale.rounding_adjustment or 0)) != 0:
                await db.refresh(sale)
                sale.rounding_adjustment = Decimal("0")
                await db.commit()
                # 抹零清零后重新计算净金额和状态
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
            Decimal(str(sale.gross_amount or 0))
            - Decimal(str(sale.scan_fee or 0))
            - Decimal(str(sale.rounding_adjustment or 0))
            - Decimal(str(sale.after_sales_adjustment or 0))
            - Decimal(str(sale.discount or 0))
            - Decimal(str(sale.commission or 0))
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
