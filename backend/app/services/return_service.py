"""
退货模块 Service — 三文鱼PMS
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ReturnOrder, ReturnItem, ReturnAttachment,
    ReturnReason, ReturnStatus, RefundMethod, ReturnAttachmentType,
    WholeFishSale, WholeFishSaleItem, FinishedProductSale, FinishedProductSaleItem,
    Company, BankAccount, TransactionRecord, TransactionType, TransactionCategory,
    ImportInvoice, BatchInvoice, MaterialTraceability, DailySlaughterRecord,
    SalesStatus, User,
)
from app.schemas.returns import ReturnOrderCreate, ReturnOrderUpdate, ReturnOrderRefund


class ReturnService:
    """退货管理服务"""

    # ==================== 查询 ====================

    @staticmethod
    async def get_return_order(db: AsyncSession, return_order_id: int) -> Optional[ReturnOrder]:
        result = await db.execute(
            select(ReturnOrder)
            .options(
                selectinload(ReturnOrder.items),
                selectinload(ReturnOrder.attachments),
            )
            .where(ReturnOrder.id == return_order_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_return_orders(
        db: AsyncSession,
        sale_type: Optional[str] = None,
        customer_id: Optional[int] = None,
        processing_plant_id: Optional[int] = None,
        status: Optional[ReturnStatus] = None,
        return_reason: Optional[ReturnReason] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ReturnOrder], int]:
        query = select(ReturnOrder).options(
            selectinload(ReturnOrder.items),
            selectinload(ReturnOrder.attachments),
        )
        count_query = select(func.count(ReturnOrder.id))

        filters = []
        if sale_type:
            filters.append(ReturnOrder.sale_type == sale_type)
        if customer_id:
            filters.append(ReturnOrder.customer_id == customer_id)
        if processing_plant_id:
            filters.append(ReturnOrder.processing_plant_id == processing_plant_id)
        if status:
            filters.append(ReturnOrder.status == status)
        if start_date:
            filters.append(ReturnOrder.return_date >= start_date)
        if end_date:
            filters.append(ReturnOrder.return_date <= end_date)
        if search:
            search_filter = or_(
                ReturnOrder.return_no.ilike(f"%{search}%"),
                Company.name.ilike(f"%{search}%"),
                ReturnOrder.problem_description.ilike(f"%{search}%"),
            )
            filters.append(search_filter)
            query = query.join(Company, ReturnOrder.customer_id == Company.id, isouter=True)
            count_query = count_query.join(Company, ReturnOrder.customer_id == Company.id, isouter=True)

        # 按退货原因筛选（join return_items）
        if return_reason:
            query = query.join(ReturnItem, ReturnItem.return_order_id == ReturnOrder.id)
            count_query = count_query.join(ReturnItem, ReturnItem.return_order_id == ReturnOrder.id)
            filters.append(ReturnItem.return_reason == return_reason)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        query = query.order_by(desc(ReturnOrder.return_date), desc(ReturnOrder.id))
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return list(items), total

    # ==================== 生成单号 ====================

    @staticmethod
    async def _generate_return_no(db: AsyncSession) -> str:
        """生成退货单号: THYYYYMMDD-NNN"""
        today = date.today()
        prefix = f"TH{today.strftime('%Y%m%d')}"

        result = await db.execute(
            select(func.max(ReturnOrder.return_no)).where(ReturnOrder.return_no.like(f"{prefix}-%"))
        )
        max_no = result.scalar() or f"{prefix}-000"
        try:
            seq = int(max_no.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1

        return f"{prefix}-{seq:03d}"

    # ==================== 加工厂自动识别 ====================

    @staticmethod
    async def _detect_processing_plant(db: AsyncSession, sale_type: str, sale_id: int) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """自动识别加工厂，返回 (plant_id, plant_name, eu_no)"""
        if sale_type == "whole_fish":
            result = await db.execute(
                select(WholeFishSale).where(WholeFishSale.id == sale_id)
            )
            sale = result.scalar_one_or_none()
            if sale and sale.batch_id:
                bi_result = await db.execute(
                    select(BatchInvoice).where(BatchInvoice.batch_id == sale.batch_id).limit(1)
                )
                bi = bi_result.scalar_one_or_none()
                if bi:
                    inv_result = await db.execute(
                        select(ImportInvoice).where(ImportInvoice.id == bi.invoice_id)
                    )
                    inv = inv_result.scalar_one_or_none()
                    if inv and inv.processing_plant_id:
                        comp_result = await db.execute(
                            select(Company.name, Company.eu_registration_no).where(Company.id == inv.processing_plant_id)
                        )
                        row = comp_result.one_or_none()
                        if row:
                            return inv.processing_plant_id, row[0], row[1]
                        return inv.processing_plant_id, None, None

        elif sale_type == "finished_product":
            # 追溯链
            trace_result = await db.execute(
                select(MaterialTraceability)
                .where(MaterialTraceability.finished_product_sale_id == sale_id)
                .limit(1)
            )
            trace = trace_result.scalar_one_or_none()
            if trace and trace.source_invoice_id:
                inv_result = await db.execute(
                    select(ImportInvoice).where(ImportInvoice.id == trace.source_invoice_id)
                )
                inv = inv_result.scalar_one_or_none()
                if inv and inv.processing_plant_id:
                    comp_result = await db.execute(
                        select(Company.name, Company.eu_registration_no).where(Company.id == inv.processing_plant_id)
                    )
                    row = comp_result.one_or_none()
                    if row:
                        return inv.processing_plant_id, row[0], row[1]
                    return inv.processing_plant_id, None, None

            # 追溯链找不到，尝试宰杀记录
            fp_result = await db.execute(
                select(FinishedProductSale).where(FinishedProductSale.id == sale_id)
            )
            fp_sale = fp_result.scalar_one_or_none()
            if fp_sale:
                ds_result = await db.execute(
                    select(DailySlaughterRecord)
                    .where(DailySlaughterRecord.source_sale_id == sale_id)
                    .limit(1)
                )
                ds = ds_result.scalar_one_or_none()
                if ds and ds.source_invoice_id:
                    inv_result = await db.execute(
                        select(ImportInvoice).where(ImportInvoice.id == ds.source_invoice_id)
                    )
                    inv = inv_result.scalar_one_or_none()
                    if inv and inv.processing_plant_id:
                        comp_result = await db.execute(
                            select(Company.name, Company.eu_registration_no).where(Company.id == inv.processing_plant_id)
                        )
                        row = comp_result.one_or_none()
                        if row:
                            return inv.processing_plant_id, row[0], row[1]
                        return inv.processing_plant_id, None, None

        return None, None, None

    # ==================== 创建退货单 ====================

    @staticmethod
    async def create_return_order(db: AsyncSession, data: dict, created_by_id: Optional[int] = None) -> ReturnOrder:
        items_data = data.pop("items", [])

        # 校验：退货金额不能超过销售金额
        sale_type = data.get("sale_type")
        sale_id = data.get("whole_fish_sale_id") or data.get("finished_product_sale_id")
        if sale_id:
            await ReturnService._validate_return_amount(db, sale_type, sale_id, items_data)

        # 自动识别加工厂
        if not data.get("processing_plant_id") and sale_id:
            plant_id, plant_name, eu_no = await ReturnService._detect_processing_plant(db, sale_type, sale_id)
            if plant_id:
                data["processing_plant_id"] = plant_id
                data["processing_plant_name"] = plant_name
                data["processing_plant_eu_no"] = eu_no

        # 计算汇总
        total_weight = Decimal("0")
        total_amount = Decimal("0")
        for item in items_data:
            w = Decimal(str(item.get("weight_kg", 0) or 0))
            p = Decimal(str(item.get("unit_price", 0) or 0))
            total_weight += w
            total_amount += w * p

        # 转换退款方式（前端小写值 → 枚举成员）
        if "refund_method" in data and data["refund_method"]:
            try:
                data["refund_method"] = RefundMethod[data["refund_method"].upper()]
            except (KeyError, ValueError):
                pass

        # 生成退货单号
        return_no = await ReturnService._generate_return_no(db)

        order = ReturnOrder(
            return_no=return_no,
            total_weight_kg=total_weight,
            total_quantity=len(items_data),
            total_amount=total_amount,
            created_by_id=created_by_id,
            **data,
        )
        db.add(order)
        await db.flush()

        # 创建明细（简化版：只保留重量、单价、金额）
        for item_data in items_data:
            w = Decimal(str(item_data.get("weight_kg", 0) or 0))
            p = Decimal(str(item_data.get("unit_price", 0) or 0))
            item = ReturnItem(
                return_order_id=order.id,
                weight_kg=w,
                unit_price=p,
                amount=w * p,
                remarks=item_data.get("remarks") or item_data.get("reason_detail") or None,
            )
            db.add(item)

        # 同步销售单售后金额
        await ReturnService._sync_sale_after_sales(db, order)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def _validate_return_amount(db: AsyncSession, sale_type: str, sale_id: int, items_data: List[dict]):
        """校验退货总额不超过销售金额"""
        from fastapi import HTTPException

        total_return = Decimal("0")
        for item in items_data:
            w = Decimal(str(item.get("weight_kg", 0) or 0))
            p = Decimal(str(item.get("unit_price", 0) or 0))
            total_return += w * p

        # 查询该销售单已有退货金额
        if sale_type == "whole_fish":
            sale_result = await db.execute(select(WholeFishSale).where(WholeFishSale.id == sale_id))
            sale = sale_result.scalar_one_or_none()
            if not sale:
                raise HTTPException(status_code=404, detail="整鱼销售单不存在")
            existing_result = await db.execute(
                select(func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")))
                .where(
                    ReturnOrder.whole_fish_sale_id == sale_id,
                    ReturnOrder.status != ReturnStatus.CANCELLED,
                )
            )
        else:
            sale_result = await db.execute(select(FinishedProductSale).where(FinishedProductSale.id == sale_id))
            sale = sale_result.scalar_one_or_none()
            if not sale:
                raise HTTPException(status_code=404, detail="成品销售单不存在")
            existing_result = await db.execute(
                select(func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")))
                .where(
                    ReturnOrder.finished_product_sale_id == sale_id,
                    ReturnOrder.status != ReturnStatus.CANCELLED,
                )
            )

        existing_return = existing_result.scalar() or Decimal("0")
        gross_amount = sale.gross_amount or Decimal("0")

        if total_return + existing_return > gross_amount:
            raise HTTPException(
                status_code=400,
                detail=f"退货总额(¥{total_return + existing_return})超过销售金额(¥{gross_amount})"
            )

    # ==================== 更新退货单 ====================

    @staticmethod
    async def update_return_order(db: AsyncSession, order: ReturnOrder, data: dict) -> ReturnOrder:
        from fastapi import HTTPException

        # 允许编辑草稿/待审批/已完成的退货单（已完成的历史数据允许补录修正）
        if order.status not in [ReturnStatus.DRAFT, ReturnStatus.PENDING_APPROVAL, ReturnStatus.COMPLETED]:
            raise HTTPException(status_code=400, detail=f"退货单状态为{order.status.value}，不能修改")

        items_data = data.pop("items", None)

        # 更新主表字段（含退款方式转换）
        for field, value in data.items():
            if value is not None:
                if field == "refund_method" and isinstance(value, str):
                    try:
                        value = RefundMethod[value.upper()]
                    except (KeyError, ValueError):
                        pass
                setattr(order, field, value)

        # 如果提供了 items，替换明细
        if items_data is not None:
            # 删除旧明细
            old_result = await db.execute(
                select(ReturnItem).where(ReturnItem.return_order_id == order.id)
            )
            for old in old_result.scalars().all():
                await db.delete(old)
            await db.flush()

            # 重新校验
            sale_type = order.sale_type
            sale_id = order.whole_fish_sale_id or order.finished_product_sale_id
            if sale_id:
                # 校验时不包含当前退货单自己
                await ReturnService._validate_return_amount_for_update(db, sale_type, sale_id, order.id, items_data)

            # 创建新明细（简化版）
            total_weight = Decimal("0")
            total_amount = Decimal("0")
            for item_data in items_data:
                w = Decimal(str(item_data.get("weight_kg", 0) or 0))
                p = Decimal(str(item_data.get("unit_price", 0) or 0))
                total_weight += w
                total_amount += w * p

                item = ReturnItem(
                    return_order_id=order.id,
                    weight_kg=w,
                    unit_price=p,
                    amount=w * p,
                    remarks=item_data.get("remarks") or item_data.get("reason_detail") or None,
                )
                db.add(item)

            order.total_weight_kg = total_weight
            order.total_quantity = len(items_data)
            order.total_amount = total_amount

        # 同步销售单
        await ReturnService._sync_sale_after_sales(db, order)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def _validate_return_amount_for_update(db: AsyncSession, sale_type: str, sale_id: int, exclude_order_id: int, items_data: List[dict]):
        total_return = Decimal("0")
        for item in items_data:
            w = Decimal(str(item.get("weight_kg", 0) or 0))
            p = Decimal(str(item.get("unit_price", 0) or 0))
            total_return += w * p

        if sale_type == "whole_fish":
            sale_result = await db.execute(select(WholeFishSale).where(WholeFishSale.id == sale_id))
            sale = sale_result.scalar_one_or_none()
            existing_result = await db.execute(
                select(func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")))
                .where(
                    ReturnOrder.whole_fish_sale_id == sale_id,
                    ReturnOrder.status != ReturnStatus.CANCELLED,
                    ReturnOrder.id != exclude_order_id,
                )
            )
        else:
            sale_result = await db.execute(select(FinishedProductSale).where(FinishedProductSale.id == sale_id))
            sale = sale_result.scalar_one_or_none()
            existing_result = await db.execute(
                select(func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")))
                .where(
                    ReturnOrder.finished_product_sale_id == sale_id,
                    ReturnOrder.status != ReturnStatus.CANCELLED,
                    ReturnOrder.id != exclude_order_id,
                )
            )

        existing_return = existing_result.scalar() or Decimal("0")
        gross_amount = sale.gross_amount or Decimal("0")

        if total_return + existing_return > gross_amount:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"退货总额(¥{total_return + existing_return})超过销售金额(¥{gross_amount})"
            )

    # ==================== 删除退货单 ====================

    @staticmethod
    async def delete_return_order(db: AsyncSession, order: ReturnOrder) -> None:
        from fastapi import HTTPException
        if order.status not in [ReturnStatus.DRAFT, ReturnStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="只有草稿或已取消的退货单可以删除")

        # 删除前同步清零销售单
        order.status = ReturnStatus.CANCELLED  # 标记为取消以排除金额计算
        await ReturnService._sync_sale_after_sales(db, order)

        await db.delete(order)
        await db.commit()

    # ==================== 审批流程 ====================

    @staticmethod
    async def submit_for_approval(db: AsyncSession, order: ReturnOrder) -> ReturnOrder:
        from fastapi import HTTPException
        if order.status != ReturnStatus.DRAFT:
            raise HTTPException(status_code=400, detail="只有草稿状态可以提交审批")
        order.status = ReturnStatus.PENDING_APPROVAL
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def approve(db: AsyncSession, order: ReturnOrder, approved_by_id: int, notes: Optional[str] = None) -> ReturnOrder:
        from fastapi import HTTPException
        if order.status != ReturnStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="只有待审批状态的退货单可以审批")
        order.status = ReturnStatus.APPROVED
        order.approved_by_id = approved_by_id
        order.approved_at = datetime.now()
        if notes:
            order.internal_notes = (order.internal_notes or "") + f"\n[审批通过] {notes}"
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def reject(db: AsyncSession, order: ReturnOrder, approved_by_id: int, notes: Optional[str] = None) -> ReturnOrder:
        from fastapi import HTTPException
        if order.status != ReturnStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="只有待审批状态的退货单可以审批")
        order.status = ReturnStatus.REJECTED
        order.approved_by_id = approved_by_id
        order.approved_at = datetime.now()
        if notes:
            order.internal_notes = (order.internal_notes or "") + f"\n[审批拒绝] {notes}"
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def cancel(db: AsyncSession, order: ReturnOrder) -> ReturnOrder:
        from fastapi import HTTPException
        if order.status == ReturnStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="已完成的退货单不能取消")
        order.status = ReturnStatus.CANCELLED
        await ReturnService._sync_sale_after_sales(db, order)
        await db.commit()
        await db.refresh(order)
        return order

    # ==================== 退款处理 ====================

    @staticmethod
    async def process_refund(db: AsyncSession, order: ReturnOrder, refund_data: ReturnOrderRefund, processed_by_id: int) -> ReturnOrder:
        from fastapi import HTTPException

        if order.status != ReturnStatus.APPROVED:
            raise HTTPException(status_code=400, detail="只有已批准状态的退货单可以执行退款")

        refund_amount = refund_data.refund_amount or order.total_amount
        refund_date = refund_data.refund_date or date.today()

        order.refund_method = refund_data.refund_method
        order.refund_amount = refund_amount
        order.refund_date = refund_date
        order.bank_account_id = refund_data.bank_account_id
        # 简化流程：执行退款后直接完成
        order.status = ReturnStatus.COMPLETED

        # 获取客户信息
        customer_result = await db.execute(select(Company).where(Company.id == order.customer_id))
        customer = customer_result.scalar_one_or_none()

        # 根据退款方式处理
        if refund_data.refund_method == RefundMethod.DIRECT_REFUND:
            # 生成支出交易流水
            transaction = TransactionRecord(
                transaction_date=refund_date,
                type=TransactionType.EXPENSE,
                category=TransactionCategory.SALES_REFUND,
                amount=refund_amount,
                from_account_id=refund_data.bank_account_id,
                counterparty_id=order.customer_id,
                counterparty_name=customer.name if customer else None,
                description=f"退货退款 {order.return_no}",
                reference_no=order.return_no,
                notes=refund_data.notes,
            )
            db.add(transaction)
            await db.flush()
            order.transaction_id = transaction.id

        elif refund_data.refund_method == RefundMethod.BALANCE_DEDUCTION:
            # 抵扣货款：减少客户应收款，不生成交易流水（不涉及资金进出）
            pass

        elif refund_data.refund_method == RefundMethod.PREPAYMENT:
            # 转为预付款：增加客户预付余额
            if customer:
                customer.prepaid_balance = (customer.prepaid_balance or Decimal("0")) + refund_amount
                transaction = TransactionRecord(
                    transaction_date=refund_date,
                    type=TransactionType.INCOME,
                    category=TransactionCategory.CUSTOMER_DEPOSIT,
                    amount=refund_amount,
                    counterparty_id=order.customer_id,
                    counterparty_name=customer.name if customer else None,
                    description=f"退货转预付款 {order.return_no}",
                    reference_no=order.return_no,
                    notes=refund_data.notes,
                )
                db.add(transaction)
                await db.flush()
                order.transaction_id = transaction.id

        elif refund_data.refund_method == RefundMethod.DEFERRED:
            # 挂账：不生成交易流水，仅记录状态
            pass

        order.status = ReturnStatus.COMPLETED
        await ReturnService._sync_sale_after_sales(db, order)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def revert_completed(db: AsyncSession, order: ReturnOrder, notes: Optional[str] = None) -> ReturnOrder:
        """撤销已完成的退货单，打回草稿状态"""
        from fastapi import HTTPException
        if order.status != ReturnStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="只有已完成的退货单可以撤销")
        
        # 打回草稿
        order.status = ReturnStatus.DRAFT
        # 清空审批/退款信息
        order.approved_by_id = None
        order.approved_at = None
        order.refund_amount = Decimal("0")
        order.refund_date = None
        order.bank_account_id = None
        order.transaction_id = None
        
        # 记录撤销备注
        if notes:
            order.internal_notes = (order.internal_notes or "") + f"\n[撤销完成] {notes}"
        else:
            order.internal_notes = (order.internal_notes or "") + "\n[撤销完成] 已撤销完成状态，打回草稿"
        
        # 同步销售单售后金额
        await ReturnService._sync_sale_after_sales(db, order)
        
        await db.commit()
        await db.refresh(order)
        return order

    # ==================== 销售单状态同步 ====================

    @staticmethod
    async def _sync_sale_after_sales(db: AsyncSession, order: ReturnOrder):
        """退货单状态变更时，同步更新销售单的 after_sales_adjustment"""
        sale = None
        if order.sale_type == "whole_fish" and order.whole_fish_sale_id:
            result = await db.execute(
                select(WholeFishSale).where(WholeFishSale.id == order.whole_fish_sale_id)
            )
            sale = result.scalar_one_or_none()
        elif order.sale_type == "finished_product" and order.finished_product_sale_id:
            result = await db.execute(
                select(FinishedProductSale).where(FinishedProductSale.id == order.finished_product_sale_id)
            )
            sale = result.scalar_one_or_none()

        if not sale:
            return

        # 计算该销售单所有有效退货单的总金额
        total_return = Decimal("0")
        for ro in sale.return_orders:
            if ro.status not in [ReturnStatus.CANCELLED, ReturnStatus.REJECTED]:
                total_return += ro.total_amount or Decimal("0")

        # 加上旧的 aftersales 金额
        old_aftersales = Decimal("0")
        if hasattr(sale, 'aftersales'):
            old_aftersales = sum(a.amount for a in (sale.aftersales or []))
        elif hasattr(sale, 'aftersales_records'):
            old_aftersales = sum(a.amount for a in (sale.aftersales_records or []))

        sale.after_sales_adjustment = total_return + old_aftersales

        # 重新计算净金额
        sale.net_amount = max(
            Decimal("0"),
            sale.gross_amount
            - (sale.scan_fee or Decimal("0"))
            - (sale.rounding_adjustment or Decimal("0"))
            - sale.after_sales_adjustment
            - (sale.discount or Decimal("0"))
            - (sale.commission or Decimal("0"))
        )

        # 更新收款状态
        paid = sale.paid_amount or Decimal("0")
        net = sale.net_amount or Decimal("0")
        if paid >= net:
            sale.status = SalesStatus.FULLY_PAID
        elif paid > 0:
            sale.status = SalesStatus.PARTIAL_PAID
        else:
            sale.status = SalesStatus.PENDING

        # 如果有进行中的退货，标记为售后中
        if any(
            r.status in [ReturnStatus.DRAFT, ReturnStatus.PENDING_APPROVAL, ReturnStatus.APPROVED]
            for r in sale.return_orders
        ):
            sale.status = SalesStatus.AFTER_SALES

    # ==================== 附件管理 ====================

    @staticmethod
    async def add_attachment(db: AsyncSession, return_order_id: int, file_info: dict) -> ReturnAttachment:
        attachment = ReturnAttachment(
            return_order_id=return_order_id,
            file_type=file_info["file_type"],
            original_name=file_info["original_name"],
            file_name=file_info["file_name"],
            file_path=file_info["file_path"],
            file_size=file_info.get("file_size", 0),
            mime_type=file_info.get("mime_type"),
            description=file_info.get("description"),
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment

    @staticmethod
    async def delete_attachment(db: AsyncSession, attachment: ReturnAttachment) -> None:
        await db.delete(attachment)
        await db.commit()

    # ==================== 统计报表 ====================

    @staticmethod
    async def get_stats(
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sale_type: Optional[str] = None,
    ) -> dict:
        """退货综合统计"""
        base_filter = []
        if start_date:
            base_filter.append(ReturnOrder.return_date >= start_date)
        if end_date:
            base_filter.append(ReturnOrder.return_date <= end_date)
        if sale_type:
            base_filter.append(ReturnOrder.sale_type == sale_type)

        # 只统计非取消/拒绝的退货单
        status_filter = ReturnOrder.status.notin_([ReturnStatus.CANCELLED, ReturnStatus.REJECTED])

        # 汇总
        from sqlalchemy import case
        summary_result = await db.execute(
            select(
                func.count(ReturnOrder.id),
                func.coalesce(func.sum(ReturnOrder.total_weight_kg), Decimal("0")),
                func.coalesce(func.sum(ReturnOrder.total_quantity), 0),
                func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")),
                func.coalesce(func.sum(ReturnOrder.refund_amount), Decimal("0")),
                func.coalesce(func.sum(case((ReturnOrder.status == ReturnStatus.PENDING_APPROVAL, 1), else_=0)), 0),
                func.coalesce(func.sum(case((ReturnOrder.status == ReturnStatus.APPROVED, 1), else_=0)), 0),
                func.coalesce(func.sum(case((ReturnOrder.status == ReturnStatus.COMPLETED, 1), else_=0)), 0),
                func.coalesce(func.sum(case((ReturnOrder.status == ReturnStatus.REJECTED, 1), else_=0)), 0),
            ).where(and_(status_filter, *base_filter))
        )
        summary_row = summary_result.one()

        # 按原因统计（退货原因现在在问题描述中，不再按原因统计）
        by_reason = []

        # 按加工厂统计
        plant_result = await db.execute(
            select(
                ReturnOrder.processing_plant_id,
                ReturnOrder.processing_plant_name,
                func.count(ReturnOrder.id),
                func.coalesce(func.sum(ReturnOrder.total_weight_kg), Decimal("0")),
                func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")),
            )
            .where(and_(status_filter, *base_filter, ReturnOrder.processing_plant_id.isnot(None)))
            .group_by(ReturnOrder.processing_plant_id, ReturnOrder.processing_plant_name)
            .order_by(desc(func.count(ReturnOrder.id)))
        )
        by_plant = [
            {
                "processing_plant_id": row[0],
                "processing_plant_name": row[1] or "未知加工厂",
                "count": row[2],
                "weight_kg": row[3],
                "amount": row[4],
            }
            for row in plant_result.all()
        ]

        # 按客户统计
        customer_result = await db.execute(
            select(
                ReturnOrder.customer_id,
                Company.name,
                func.count(ReturnOrder.id),
                func.coalesce(func.sum(ReturnOrder.total_weight_kg), Decimal("0")),
                func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")),
            )
            .join(Company, ReturnOrder.customer_id == Company.id)
            .where(and_(status_filter, *base_filter))
            .group_by(ReturnOrder.customer_id, Company.name)
            .order_by(desc(func.count(ReturnOrder.id)))
        )
        by_customer = [
            {
                "customer_id": row[0],
                "customer_name": row[1],
                "count": row[2],
                "weight_kg": row[3],
                "amount": row[4],
            }
            for row in customer_result.all()
        ]

        # 按产品统计 — 退货明细已简化，不再按产品统计
        by_product = []

        # 趋势（按月）
        period_expr = func.to_char(ReturnOrder.return_date, 'YYYY-MM')
        trend_result = await db.execute(
            select(
                period_expr.label("period"),
                func.count(ReturnOrder.id),
                func.coalesce(func.sum(ReturnOrder.total_weight_kg), Decimal("0")),
                func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")),
            )
            .where(and_(status_filter, *base_filter))
            .group_by(period_expr)
            .order_by(period_expr)
        )
        trend = [
            {
                "period": row[0],
                "count": row[1],
                "weight_kg": row[2],
                "amount": row[3],
            }
            for row in trend_result.all()
        ]

        return {
            "summary": {
                "total_return_orders": summary_row[0],
                "total_return_weight_kg": summary_row[1],
                "total_return_quantity": summary_row[2],
                "total_return_amount": summary_row[3],
                "total_refund_amount": summary_row[4],
                "pending_count": summary_row[5],
                "approved_count": summary_row[6],
                "completed_count": summary_row[7],
                "rejected_count": summary_row[8],
            },
            "by_reason": by_reason,
            "by_plant": by_plant,
            "by_customer": by_customer,
            "by_product": by_product,
            "trend": trend,
        }

    @staticmethod
    def _get_reason_label(reason: ReturnReason) -> str:
        labels = {
            ReturnReason.QUALITY_ISSUE: "质量问题",
            ReturnReason.LOGISTICS_DAMAGE: "物流损坏",
            ReturnReason.SPEC_MISMATCH: "规格不符",
            ReturnReason.TEMPERATURE_ISSUE: "温控问题",
            ReturnReason.FOREIGN_MATTER: "异物混入",
            ReturnReason.CUSTOMER_REASON: "客户原因",
            ReturnReason.EXPIRED: "临期/过期",
            ReturnReason.OTHER: "其他",
        }
        return labels.get(reason, str(reason))
