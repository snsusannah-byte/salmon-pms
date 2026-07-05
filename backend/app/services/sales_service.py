from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AftersalesRecord,
    Batch,
    Company,
    ReturnOrder,
    SalesReceipt,
    SalesStatus,
    WholeFishSale,
    WholeFishSaleItem,
)


class SalesService:
    """销售管理服务"""

    @staticmethod
    async def get_sale_by_id(db: AsyncSession, sale_id: int) -> WholeFishSale | None:
        result = await db.execute(
            select(WholeFishSale)
            .options(
                selectinload(WholeFishSale.items),
                selectinload(WholeFishSale.receipts),
                selectinload(WholeFishSale.aftersales),
                selectinload(WholeFishSale.return_orders).selectinload(ReturnOrder.items),
            )
            .where(WholeFishSale.id == sale_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_sales(
        db: AsyncSession,
        batch_id: int | None = None,
        customer_id: int | None = None,
        ids: list[int] | None = None,
        status: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[WholeFishSale], int]:
        from sqlalchemy import or_
        
        query = select(WholeFishSale).options(
            selectinload(WholeFishSale.items),
            selectinload(WholeFishSale.receipts),
            selectinload(WholeFishSale.aftersales),
            selectinload(WholeFishSale.return_orders).selectinload(ReturnOrder.items),
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
            # 支持逗号分隔的多选状态
            status_list = [s.strip() for s in status.split(",") if s.strip()]
            has_aftersales = "has_aftersales" in status_list
            status_list = [s for s in status_list if s != "has_aftersales"]
            if len(status_list) == 1:
                filters.append(WholeFishSale.status == status_list[0])
            elif len(status_list) > 1:
                filters.append(WholeFishSale.status.in_(status_list))
            if has_aftersales:
                filters.append(WholeFishSale.after_sales_adjustment > 0)

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
        
        # 如果客户是内部加工厂，自动标记为内部销售
        if sale.customer_id:
            from app.models import Company
            customer_result = await db.execute(
                select(Company).where(Company.id == sale.customer_id)
            )
            customer = customer_result.scalar_one_or_none()
            if customer and customer.customer_type == "internal_processor":
                sale.is_internal_sale = True
        
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
        
        # 5. 自动创建出库单（从进口整包仓扣减库存）- 在 commit 之前完成
        if sale.box_count and sale.box_count > 0:
            try:
                from app.services.warehouse_v2_service import WarehouseV2Service
                from app.models import Batch, BatchInvoice, ImportInvoice, InvoiceProduct, Product, Stock, StockMovement, StockMovementType, StockStatus
                from sqlalchemy import func
                
                warehouse_id = 1  # ZB-IMPORT 进口整包仓
                
                # 获取批次关联的发票及产品
                batch_result = await db.execute(
                    select(Batch).where(Batch.id == sale.batch_id)
                )
                batch = batch_result.scalar_one_or_none()
                
                if batch:
                    # 查找批次下的发票（通过 BatchInvoice 关联表）
                    invoice_result = await db.execute(
                        select(ImportInvoice)
                        .join(BatchInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
                        .where(BatchInvoice.batch_id == batch.id)
                        .limit(1)
                    )
                    invoice = invoice_result.scalar_one_or_none()
                    
                    if invoice:
                        # 查找发票产品明细
                        product_result = await db.execute(
                            select(InvoiceProduct).where(
                                InvoiceProduct.invoice_id == invoice.id
                            ).limit(1)
                        )
                        inv_product = product_result.scalar_one_or_none()
                        
                        if inv_product:
                            # 查找对应的产品ID
                            db_product_result = await db.execute(
                                select(Product.id).where(
                                    Product.name == inv_product.product_name
                                ).limit(1)
                            )
                            product_id = db_product_result.scalar()
                            
                            if product_id:
                                # 创建出库单（不调用会commit的service方法，直接操作）
                                today = sale.sale_date or date.today()
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
                                    dest_type="sale",
                                    dest_id=sale.id,
                                    dest_no=sale.sale_no,
                                    warehouse_id=warehouse_id,
                                    product_id=product_id,
                                    batch_id=sale.batch_id,
                                    qty=Decimal(str(sale.weight_kg)),
                                    unit="kg",
                                    box_count=sale.box_count or 0,
                                    outbound_date=sale.sale_date,
                                    status=StockStatus.PENDING,
                                    notes=f"规格：{sale.spec}",
                                )
                                db.add(outbound)
                                await db.flush()  # 获取 outbound.id
                                
                                # 确认出库（直接操作，不调用会commit的service方法）
                                stock = await WarehouseV2Service.get_or_create_stock(
                                    db, warehouse_id, product_id, sale.batch_id, "kg"
                                )
                                
                                if stock.available_box_count >= outbound.box_count:
                                    qty_before = stock.current_qty
                                    box_count_before = stock.current_box_count
                                    
                                    stock.current_qty = (stock.current_qty - outbound.qty).quantize(Decimal("0.001"))
                                    stock.available_qty = (stock.current_qty - stock.reserved_qty).quantize(Decimal("0.001"))
                                    stock.last_out_date = outbound.outbound_date
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
            except Exception as e:
                # 自动出库失败不阻塞销售单创建，记录日志
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"销售单 {sale.sale_no} 自动出库失败: {e}")
        
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
        
        # 同步提成记录（同时更新 sale.commission）
        await SalesService._sync_commission_record(db, sale)
        
        # 再次重新计算净金额（确保 commission 变化后同步）
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
        
        # 如果没有业务员，不生成提成记录，同时清零 sale.commission
        if not sale.salesperson_id:
            sale.commission = Decimal("0")
            return
        
        # 获取业务员提成单价
        result = await db.execute(select(Salesperson).where(Salesperson.id == sale.salesperson_id))
        sp = result.scalar_one_or_none()
        if not sp or not sp.is_active:
            sale.commission = Decimal("0")
            return
        
        rate = Decimal(str(sp.commission_rate or 0))
        weight = Decimal(str(sale.weight_kg or 0))
        commission_amount = (weight * rate).quantize(Decimal("0.01"))
        
        # 同步更新 sale.commission 字段（确保 net_amount 计算一致）
        sale.commission = commission_amount
        
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
        from fastapi import HTTPException

        from app.models import TransactionCategory, TransactionRecord, TransactionType
        sale = await SalesService.get_sale_by_id(db, sale_id)
        if not sale:
            raise HTTPException(status_code=404, detail="销售记录不存在")
        if sale.is_locked:
            raise HTTPException(status_code=400, detail="销售记录已锁定")

        # 获取实收金额
        received_amount = Decimal(str(data.get("amount", 0)))
        if received_amount <= 0:
            raise HTTPException(status_code=400, detail="收款金额必须大于0")

        # 余额抵扣：校验客户余额充足
        is_balance_payment = data.get("payment_method") == "balance"
        if is_balance_payment:
            if not sale.customer_id:
                raise HTTPException(status_code=400, detail="销售单未绑定客户，无法使用余额抵扣")
            company_result = await db.execute(
                select(Company).where(Company.id == sale.customer_id)
            )
            company = company_result.scalar_one_or_none()
            if not company:
                raise HTTPException(status_code=404, detail="客户不存在")
            available_balance = Decimal(str(company.prepaid_balance or 0))
            if available_balance <= 0:
                raise HTTPException(status_code=400, detail="客户预付款余额为0，无法使用余额抵扣")
            # 余额不足时按实际可用余额抵扣（部分收款）
            if available_balance < received_amount:
                received_amount = available_balance
                data["amount"] = float(received_amount)
            # 余额抵扣不关联银行账户
            data["bank_account_id"] = None

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

        # 非余额抵扣：同步创建交易流水（银行实际收支）
        if not is_balance_payment:
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
            
            # 查询关联发票号（通过 batch → batch_invoices → import_invoices）
            related_invoice_no = None
            if sale.batch_id:
                from app.models import BatchInvoice, ImportInvoice
                batch_inv_result = await db.execute(
                    select(ImportInvoice.invoice_no)
                    .join(BatchInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
                    .where(BatchInvoice.batch_id == sale.batch_id)
                    .order_by(BatchInvoice.id)
                )
                invoice_nos = [row[0] for row in batch_inv_result.all() if row[0]]
                if invoice_nos:
                    related_invoice_no = ", ".join(invoice_nos)
            
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
                related_invoice_no=related_invoice_no,
                is_confirmed=True,
            )
            # 设置关联销售单（JSON 数组）
            transaction.related_sale_ids = [sale.id]
            db.add(transaction)
            await db.flush()
            
            # 关联交易流水到收款记录
            receipt.transaction_id = transaction.id
        
        # 余额抵扣：扣减客户预付余额
        if is_balance_payment:
            company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) - received_amount
        
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

        # 同步删除关联的交易流水（如果存在）
        if receipt.transaction_id:
            from app.models import TransactionRecord
            trans_result = await db.execute(
                select(TransactionRecord).where(TransactionRecord.id == receipt.transaction_id)
            )
            transaction = trans_result.scalar_one_or_none()
            if transaction:
                await db.delete(transaction)

        # 余额抵扣删除：恢复客户预付余额
        if receipt.payment_method == "balance" and sale and sale.customer_id:
            company_result = await db.execute(
                select(Company).where(Company.id == sale.customer_id)
            )
            company = company_result.scalar_one_or_none()
            if company:
                refund = Decimal(str(receipt.amount or 0))
                company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) + refund

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

        # 同步销售单售后金额和状态
        await SalesService._sync_sale_after_sales(db, sale_id)
        await db.commit()

        return record

    @staticmethod
    async def update_aftersales(db: AsyncSession, record: AftersalesRecord, data: dict) -> AftersalesRecord:
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)

        # 如果金额或状态变化，同步销售单
        if "amount" in data or "status" in data:
            await SalesService._sync_sale_after_sales(db, record.sale_id)
            await db.commit()

        return record

    @staticmethod
    async def delete_aftersales(db: AsyncSession, record_id: int) -> None:
        result = await db.execute(select(AftersalesRecord).where(AftersalesRecord.id == record_id))
        record = result.scalar_one_or_none()
        if not record:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="售后记录不存在")

        sale_id = record.sale_id
        await db.delete(record)
        await db.flush()  # 确保删除生效

        # 重新同步销售单的售后金额和状态
        await SalesService._sync_sale_after_sales(db, sale_id)
        await db.commit()

    @staticmethod
    async def _sync_sale_after_sales(db: AsyncSession, sale_id: int) -> None:
        """同步销售单的 after_sales_adjustment, net_amount, status（使用直接 SQL 避免 ORM 缓存）"""
        # 直接查询基础字段
        result = await db.execute(
            select(
                WholeFishSale.gross_amount,
                WholeFishSale.scan_fee,
                WholeFishSale.rounding_adjustment,
                WholeFishSale.discount,
                WholeFishSale.commission,
                WholeFishSale.paid_amount,
            ).where(WholeFishSale.id == sale_id)
        )
        row = result.one_or_none()
        if not row:
            return

        gross, scan_fee, rounding, discount, commission, paid = row

        # 查询实际售后金额
        aftersales_result = await db.execute(
            select(func.coalesce(func.sum(AftersalesRecord.amount), Decimal("0")))
            .where(AftersalesRecord.sale_id == sale_id)
        )
        aftersales_amount = aftersales_result.scalar() or Decimal("0")

        # 查询退货单金额
        return_amount = Decimal("0")
        try:
            from app.models import ReturnOrder, ReturnStatus
            return_result = await db.execute(
                select(func.coalesce(func.sum(ReturnOrder.total_amount), Decimal("0")))
                .where(
                    ReturnOrder.whole_fish_sale_id == sale_id,
                    ReturnOrder.status.notin_([ReturnStatus.CANCELLED, ReturnStatus.REJECTED])
                )
            )
            return_amount = return_result.scalar() or Decimal("0")
        except Exception:
            pass

        new_aftersales = aftersales_amount + return_amount

        # 重新计算净金额
        new_net = max(
            Decimal("0"),
            (gross or Decimal("0"))
            - (scan_fee or Decimal("0"))
            - (rounding or Decimal("0"))
            - new_aftersales
            - (discount or Decimal("0"))
            - (commission or Decimal("0"))
        )

        # 确定正确状态
        if paid >= new_net and new_net > 0:
            new_status = SalesStatus.FULLY_PAID
        elif paid > 0:
            new_status = SalesStatus.PARTIAL_PAID
        else:
            new_status = SalesStatus.PENDING

        # 检查进行中的退货
        try:
            from app.models import ReturnOrder, ReturnStatus
            in_progress = await db.execute(
                select(func.count(ReturnOrder.id))
                .where(
                    ReturnOrder.whole_fish_sale_id == sale_id,
                    ReturnOrder.status.in_([
                        ReturnStatus.DRAFT,
                        ReturnStatus.PENDING_APPROVAL,
                        ReturnStatus.APPROVED,
                        ReturnStatus.REFUNDING,
                    ])
                )
            )
            if in_progress.scalar() > 0:
                new_status = SalesStatus.AFTER_SALES
        except Exception:
            pass

        # 使用直接 SQL UPDATE 避免 ORM 缓存问题
        await db.execute(
            update(WholeFishSale)
            .where(WholeFishSale.id == sale_id)
            .values(
                after_sales_adjustment=float(new_aftersales),
                net_amount=float(new_net),
                status=new_status,
                updated_at=datetime.now(),
            )
        )


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
