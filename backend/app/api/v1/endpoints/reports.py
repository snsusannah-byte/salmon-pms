"""
报表中心 - 批次财报 & 单票财报
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import (
    Batch,
    BatchInvoice,
    ImportInvoice,
    ImportTax,
    ClearanceCost,
    ExchangeRecord,
    ExchangeStatus,
    WholeFishSale,
    InvoiceProduct,
    Company,
    SalesReceipt,
    TransactionRecord,
    AftersalesRecord,
    BankAccount,
    CommissionRecord,
)
from app.schemas.report import (
    BatchReportSummaryItem,
    BatchReportListResponse,
    BatchReportDetail,
    BatchReportInvoiceDetail,
    InvoiceReportSummaryItem,
    InvoiceReportListResponse,
    InvoiceReportDetail,
    InvoiceProductDetail,
    InvoiceSaleDetail,
    ReceivableStatementItem,
    ReceivableCustomerItem,
    ReceivableStatementResponse,
    PayableStatementItem,
    PayableSupplierItem,
    PayableStatementResponse,
    FinancialStatements,
    FinancialStatementItem,
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
    FinancialCharts,
)

router = APIRouter()


# ==================== 辅助计算函数 ====================

async def _get_batch_sales(db: AsyncSession, batch_id: int) -> List[WholeFishSale]:
    """获取批次的所有销售记录"""
    result = await db.execute(
        select(WholeFishSale).where(WholeFishSale.batch_id == batch_id)
    )
    return result.scalars().all()


async def _get_invoice_taxes(db: AsyncSession, invoice_id: int) -> Optional[ImportTax]:
    """获取发票的税费记录"""
    result = await db.execute(
        select(ImportTax).where(ImportTax.invoice_id == invoice_id)
    )
    return result.scalar_one_or_none()


async def _get_invoice_clearance(db: AsyncSession, invoice_id: int) -> Optional[ClearanceCost]:
    """获取发票的清关费用记录"""
    result = await db.execute(
        select(ClearanceCost).where(ClearanceCost.invoice_id == invoice_id)
    )
    return result.scalar_one_or_none()


async def _get_invoice_exchange(db: AsyncSession, invoice_id: int, batch_id: Optional[int] = None) -> Optional[ExchangeRecord]:
    """获取发票/批次的购汇记录（发票优先，回退到批次）"""
    # 先按发票查
    result = await db.execute(
        select(ExchangeRecord)
        .where(ExchangeRecord.invoice_id == invoice_id)
        .order_by(ExchangeRecord.created_at.desc())
    )
    ex = result.scalar_one_or_none()
    if ex:
        return ex
    # 回退按批次查
    if batch_id:
        result = await db.execute(
            select(ExchangeRecord)
            .where(ExchangeRecord.batch_id == batch_id)
            .order_by(ExchangeRecord.created_at.desc())
        )
        return result.scalar_one_or_none()
    return None


async def _get_company_name(db: AsyncSession, company_id: Optional[int]) -> Optional[str]:
    """获取公司名称"""
    if not company_id:
        return None
    result = await db.execute(select(Company.name).where(Company.id == company_id))
    return result.scalar()


async def _get_invoice_batch_info(db: AsyncSession, invoice_id: int) -> tuple:
    """获取发票所属的批次信息 (batch_id, batch_name, batch_code)"""
    result = await db.execute(
        select(BatchInvoice, Batch)
        .join(Batch, BatchInvoice.batch_id == Batch.id)
        .where(BatchInvoice.invoice_id == invoice_id)
    )
    row = result.first()
    if row:
        bi, batch = row
        return batch.id, batch.batch_name, batch.batch_code
    return None, None, None


def _to_decimal(value) -> Decimal:
    """安全转换为Decimal"""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


async def _calculate_invoice_report_data(
    db: AsyncSession,
    invoice: ImportInvoice,
    include_sales: bool = True,
    sales_proportion: Decimal = Decimal("1"),
) -> dict:
    """
    计算单票财报的核心数据
    
    Args:
        include_sales: 是否包含销售数据
        sales_proportion: 销售分配比例 (用于合并批次中的单票)
    
    Returns:
        包含所有计算字段的字典
    """
    # 产品明细
    result = await db.execute(
        select(InvoiceProduct).where(InvoiceProduct.invoice_id == invoice.id)
    )
    products = result.scalars().all()

    total_weight = sum(_to_decimal(p.net_weight_kg) for p in products)
    total_boxes = sum(p.box_count or 0 for p in products)
    total_amount_usd = sum(_to_decimal(p.total_amount) for p in products)
    if total_amount_usd == 0:
        total_amount_usd = _to_decimal(invoice.total_amount_usd)
    if total_weight == 0:
        total_weight = _to_decimal(invoice.total_weight_kg)
    if total_boxes == 0:
        total_boxes = invoice.total_boxes or 0

    # 批次信息
    batch_id, batch_name, batch_code = await _get_invoice_batch_info(db, invoice.id)

    # 税费
    tax = await _get_invoice_taxes(db, invoice.id)
    import_duty = _to_decimal(tax.import_duty) if tax else Decimal("0")
    import_vat = _to_decimal(tax.import_vat) if tax else Decimal("0")
    total_taxes = import_duty + import_vat

    # 清关费
    clearance = await _get_invoice_clearance(db, invoice.id)
    clearance_fee = _to_decimal(clearance.clearance_fee) if clearance else Decimal("0")
    freight_fee = _to_decimal(clearance.freight_fee) if clearance else Decimal("0")
    inspection_fee = _to_decimal(clearance.inspection_fee) if clearance else Decimal("0")
    quarantine_fee = _to_decimal(clearance.quarantine_fee) if clearance else Decimal("0")
    other_costs = _to_decimal(clearance.other_costs) if clearance else Decimal("0")
    clearance_cost = clearance_fee + freight_fee + inspection_fee + quarantine_fee + other_costs

    # 购汇
    exchange = await _get_invoice_exchange(db, invoice.id, batch_id)
    exchange_rate = _to_decimal(exchange.exchange_rate) if exchange else Decimal("0")
    exchange_payment = _to_decimal(exchange.amount_cny) if exchange else Decimal("0")
    exchange_fee = _to_decimal(exchange.fee_cny) if exchange else Decimal("0")

    # 如果购汇记录没有汇率，用预估汇率或默认值
    if exchange_rate == 0 and invoice.estimated_exchange_rate:
        exchange_rate = _to_decimal(invoice.estimated_exchange_rate)
    if exchange_rate == 0:
        exchange_rate = Decimal("7.0")

    # 采购成本(CNY)
    purchase_cost_cny = total_amount_usd * exchange_rate

    # 销售数据 (批次级)
    sales_data = []
    total_sales_amount = Decimal("0")
    total_sales_net = Decimal("0")
    total_sales_weight = Decimal("0")
    total_scan_fee = Decimal("0")
    total_rounding = Decimal("0")
    total_commission = Decimal("0")
    total_after_sales = Decimal("0")
    total_discount = Decimal("0")
    sales_count = 0

    if include_sales and batch_id:
        sales_list = await _get_batch_sales(db, batch_id)
        
        # 从 CommissionRecord 表查询该批次的提成汇总
        sale_ids = [s.id for s in sales_list]
        if sale_ids:
            commission_result = await db.execute(
                select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(sale_ids))
            )
            total_commission = _to_decimal(commission_result.scalar())
        
        for sale in sales_list:
            customer_name = await _get_company_name(db, sale.customer_id)
            total_sales_amount += _to_decimal(sale.gross_amount)
            total_sales_weight += _to_decimal(sale.weight_kg)
            total_scan_fee += _to_decimal(sale.scan_fee)
            total_rounding += _to_decimal(sale.rounding_adjustment)
            total_after_sales += _to_decimal(sale.after_sales_adjustment)
            total_discount += _to_decimal(sale.discount)
            sales_count += 1

            sales_data.append({
                "sale_date": sale.sale_date,
                "customer_name": customer_name,
                "spec": sale.spec,
                "box_count": sale.box_count,
                "weight_kg": _to_decimal(sale.weight_kg),
                "unit_price": _to_decimal(sale.unit_price),
                "gross_amount": _to_decimal(sale.gross_amount),
                "scan_fee": _to_decimal(sale.scan_fee),
                "rounding_adjustment": _to_decimal(sale.rounding_adjustment),
                "commission": _to_decimal(sale.commission),
                "after_sales_adjustment": _to_decimal(sale.after_sales_adjustment),
                "discount": _to_decimal(sale.discount),
                "net_amount": _to_decimal(sale.net_amount),
            })
        
        # 重新计算销售净额（不包含 commission，commission 单独显示）
        total_sales_net = (
            total_sales_amount
            - total_scan_fee
            - total_rounding
            - total_after_sales
            - total_discount
        )

    # 按比例分配销售
    allocated_sales_net = total_sales_net * sales_proportion
    allocated_sales_weight = total_sales_weight * sales_proportion

    # 支出合计
    total_expenses = total_taxes + clearance_cost + exchange_payment + exchange_fee

    # 损耗计算
    shrinkage = Decimal("0")
    if total_weight > 0 and allocated_sales_weight > 0:
        diff = total_weight - allocated_sales_weight
        if diff > 0:
            unit_price_usd = total_amount_usd / total_weight if total_weight > 0 else Decimal("0")
            shrinkage = diff * unit_price_usd * exchange_rate
            shrinkage = round(shrinkage, 2)

    # 净利润 = (销售净额 - 业务员提成) - 支出合计 - 账面损耗
    net_profit = (allocated_sales_net - total_commission) - total_expenses - shrinkage

    # 利润率
    profit_margin = None
    if purchase_cost_cny > 0:
        profit_margin = round(net_profit / purchase_cost_cny * 100, 2)

    return {
        "invoice_id": invoice.id,
        "invoice_no": invoice.invoice_no,
        "invoice_date": invoice.invoice_date,
        "kill_date": invoice.kill_date,
        "arrival_date": invoice.arrival_date,
        "processing_plant_name": await _get_company_name(db, invoice.processing_plant_id),
        "exporter_name": await _get_company_name(db, invoice.exporter_id),
        "awb_no": invoice.awb_no,
        "gross_weight_kg": _to_decimal(invoice.gross_weight_kg),
        "batch_id": batch_id,
        "batch_name": batch_name,
        "batch_code": batch_code,

        "products": products,
        "total_amount_usd": total_amount_usd,
        "purchase_cost_cny": round(purchase_cost_cny, 2),
        "total_weight_kg": total_weight,
        "total_boxes": total_boxes,

        "import_duty": import_duty,
        "import_vat": import_vat,
        "total_taxes": total_taxes,

        "clearance_cost": clearance_cost,
        "clearance_breakdown": {
            "customs_broker": clearance.customs_broker if clearance else None,
            "clearance_fee": clearance_fee,
            "freight_fee": freight_fee,
            "inspection_fee": inspection_fee,
            "quarantine_fee": quarantine_fee,
            "other_costs": other_costs,
        },

        "exchange_rate": exchange_rate,
        "exchange_payment": exchange_payment,
        "exchange_fee": exchange_fee,

        "total_sales_amount": total_sales_amount,
        "total_sales_net": total_sales_net,
        "total_sales_weight": total_sales_weight,
        "allocated_sales_net": allocated_sales_net,
        "allocated_sales_weight": allocated_sales_weight,
        "total_scan_fee": total_scan_fee,
        "total_rounding": total_rounding,
        "total_commission": total_commission,
        "total_after_sales": total_after_sales,
        "total_discount": total_discount,
        "sales_count": sales_count,
        "sales_data": sales_data,

        "total_expenses": total_expenses,
        "shrinkage": shrinkage,
        "net_profit": round(net_profit, 2),
        "profit_margin": profit_margin,
    }


# ==================== 批次财报 ====================

@router.get("/batches", response_model=BatchReportListResponse)
async def list_batch_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=500),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """批次财报列表 - 所有批次的核心财务指标汇总"""
    # 获取批次总数
    count_result = await db.execute(select(func.count(Batch.id)))
    total = count_result.scalar() or 0

    # 获取批次列表
    batch_result = await db.execute(
        select(Batch).order_by(Batch.batch_date.desc()).offset(skip).limit(limit)
    )
    batches = batch_result.scalars().all()

    # 预计算所有已完成批次的累计利润
    cumulative_profit_map = {}
    running_cumulative = Decimal("0")
    
    all_completed_result = await db.execute(
        select(Batch.id, Batch.batch_date)
        .join(BatchInvoice, BatchInvoice.batch_id == Batch.id)
        .join(ImportInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
        .where(ImportInvoice.exchange_status == ExchangeStatus.COMPLETED)
        .distinct()
        .order_by(Batch.batch_date, Batch.id)
    )
    all_completed_batches = all_completed_result.all()
    
    for (cb_id, cb_date) in all_completed_batches:
        cb_sales_result = await db.execute(
            select(WholeFishSale).where(WholeFishSale.batch_id == cb_id)
        )
        cb_sales_list = cb_sales_result.scalars().all()
        cb_sales_net = sum(_to_decimal(s.net_amount) for s in cb_sales_list)
        
        # commission
        cb_sale_ids = [s.id for s in cb_sales_list]
        cb_commission = Decimal("0")
        if cb_sale_ids:
            cb_commission_result = await db.execute(
                select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(cb_sale_ids))
            )
            cb_commission = _to_decimal(cb_commission_result.scalar())

        cb_ex_result = await db.execute(
            select(ExchangeRecord).where(ExchangeRecord.batch_id == cb_id)
        )
        cb_ex_list = cb_ex_result.scalars().all()
        cb_ex_payment = sum(_to_decimal(e.amount_cny) for e in cb_ex_list)
        cb_ex_fee = sum(_to_decimal(e.fee_cny) for e in cb_ex_list)

        cb_bi_result = await db.execute(
            select(BatchInvoice).where(BatchInvoice.batch_id == cb_id)
        )
        cb_inv_ids = [bi.invoice_id for bi in cb_bi_result.scalars().all()]

        cb_taxes = Decimal("0")
        cb_clearance = Decimal("0")
        for cb_inv_id in cb_inv_ids:
            cb_tax = await _get_invoice_taxes(db, cb_inv_id)
            if cb_tax:
                cb_taxes += _to_decimal(cb_tax.import_vat) + _to_decimal(cb_tax.import_duty)
            cb_clearance_item = await _get_invoice_clearance(db, cb_inv_id)
            if cb_clearance_item:
                cb_clearance += (
                    _to_decimal(cb_clearance_item.clearance_fee) +
                    _to_decimal(cb_clearance_item.freight_fee) +
                    _to_decimal(cb_clearance_item.inspection_fee) +
                    _to_decimal(cb_clearance_item.quarantine_fee) +
                    _to_decimal(cb_clearance_item.other_costs)
                )

        cb_expenses = cb_ex_payment + cb_ex_fee + cb_taxes + cb_clearance
        
        # 损耗
        cb_shrinkage = Decimal("0")
        if cb_inv_ids:
            cb_prod_result = await db.execute(
                select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(cb_inv_ids))
            )
            cb_prods = cb_prod_result.scalars().all()
            cb_import_weight = sum(_to_decimal(p.net_weight_kg) for p in cb_prods)
            cb_sales_weight = sum(_to_decimal(s.weight_kg) for s in cb_sales_list)
            if cb_import_weight > cb_sales_weight and cb_sales_weight > 0:
                cb_diff = cb_import_weight - cb_sales_weight
                cb_rate = Decimal("7.0")
                if cb_ex_list and cb_ex_list[0].exchange_rate and cb_ex_list[0].exchange_rate > 0:
                    cb_rate = _to_decimal(cb_ex_list[0].exchange_rate)
                cb_import_amount = sum(_to_decimal(p.total_amount) for p in cb_prods)
                if cb_import_amount > 0 and cb_import_weight > 0:
                    cb_unit_price = cb_import_amount / cb_import_weight
                    cb_shrinkage = cb_diff * cb_unit_price * cb_rate
        
        cb_net_profit = (cb_sales_net - cb_commission) - cb_expenses - round(cb_shrinkage, 2)
        running_cumulative += cb_net_profit
        cumulative_profit_map[cb_id] = round(running_cumulative, 2)

    items: List[BatchReportSummaryItem] = []
    for batch in batches:
        # 获取关联的发票
        bi_result = await db.execute(
            select(BatchInvoice, ImportInvoice)
            .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
            .where(BatchInvoice.batch_id == batch.id)
        )
        bi_rows = bi_result.all()

        invoice_ids = []
        invoice_nos = []
        total_purchase_usd = Decimal("0")
        total_weight = Decimal("0")
        total_boxes = 0

        total_import_duty = Decimal("0")
        total_import_vat = Decimal("0")
        total_clearance = Decimal("0")
        total_exchange_payment = Decimal("0")
        total_exchange_fee = Decimal("0")
        exchange_rate = None
        batch_exchange_applied_summary = False  # 批次级购汇只计算一次

        for bi, inv in bi_rows:
            invoice_ids.append(inv.id)
            invoice_nos.append(inv.invoice_no)

            # 产品汇总
            prod_result = await db.execute(
                select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
            )
            prods = prod_result.scalars().all()
            inv_weight = sum(_to_decimal(p.net_weight_kg) for p in prods)
            inv_boxes = sum(p.box_count or 0 for p in prods)
            inv_amount = sum(_to_decimal(p.total_amount) for p in prods)
            if inv_amount == 0:
                inv_amount = _to_decimal(inv.total_amount_usd)
            if inv_weight == 0:
                inv_weight = _to_decimal(inv.total_weight_kg)
            if inv_boxes == 0:
                inv_boxes = inv.total_boxes or 0

            total_purchase_usd += inv_amount
            total_weight += inv_weight
            total_boxes += inv_boxes

            # 税费
            tax = await _get_invoice_taxes(db, inv.id)
            if tax:
                total_import_duty += _to_decimal(tax.import_duty)
                total_import_vat += _to_decimal(tax.import_vat)

            # 清关
            clearance = await _get_invoice_clearance(db, inv.id)
            if clearance:
                total_clearance += (
                    _to_decimal(clearance.clearance_fee) +
                    _to_decimal(clearance.freight_fee) +
                    _to_decimal(clearance.inspection_fee) +
                    _to_decimal(clearance.quarantine_fee) +
                    _to_decimal(clearance.other_costs)
                )

            # 购汇 (取第一个有数据的作为批次汇率参考)
            ex = await _get_invoice_exchange(db, inv.id, batch.id)
            if ex:
                if exchange_rate is None or exchange_rate == 0:
                    exchange_rate = _to_decimal(ex.exchange_rate)
                if ex.invoice_id == inv.id:
                    # 发票级别购汇
                    total_exchange_payment += _to_decimal(ex.amount_cny)
                    total_exchange_fee += _to_decimal(ex.fee_cny)
                elif not batch_exchange_applied_summary:
                    # 批次级别购汇，只计算一次
                    total_exchange_payment += _to_decimal(ex.amount_cny)
                    total_exchange_fee += _to_decimal(ex.fee_cny)
                    batch_exchange_applied_summary = True

        # 批次销售汇总
        sales_list = await _get_batch_sales(db, batch.id)
        total_sales_amount = Decimal("0")
        total_sales_net = Decimal("0")
        total_sales_weight = Decimal("0")
        total_scan_fee = Decimal("0")
        total_rounding = Decimal("0")
        total_after_sales = Decimal("0")
        total_discount = Decimal("0")
        total_commission = Decimal("0")
        
        # 从 CommissionRecord 表查询提成
        sale_ids = [s.id for s in sales_list]
        if sale_ids:
            commission_result = await db.execute(
                select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(sale_ids))
            )
            total_commission = _to_decimal(commission_result.scalar())
        
        for sale in sales_list:
            total_sales_amount += _to_decimal(sale.gross_amount)
            total_scan_fee += _to_decimal(sale.scan_fee)
            total_rounding += _to_decimal(sale.rounding_adjustment)
            total_after_sales += _to_decimal(sale.after_sales_adjustment)
            total_discount += _to_decimal(sale.discount)
            total_sales_weight += _to_decimal(sale.weight_kg)
        
        # 重新计算销售净额（不包含 commission）
        total_sales_net = (
            total_sales_amount
            - total_scan_fee
            - total_rounding
            - total_after_sales
            - total_discount
        )

        # 汇率默认值
        if exchange_rate is None or exchange_rate == 0:
            exchange_rate = Decimal("7.0")

        # 采购成本(CNY)
        total_purchase_cny = total_purchase_usd * exchange_rate

        # 支出合计
        total_taxes = total_import_duty + total_import_vat
        total_expenses = total_taxes + total_clearance + total_exchange_payment + total_exchange_fee

        # 损耗
        shrinkage = Decimal("0")
        if total_weight > 0 and total_sales_weight > 0:
            diff = total_weight - total_sales_weight
            if diff > 0:
                unit_price_usd = total_purchase_usd / total_weight if total_weight > 0 else Decimal("0")
                shrinkage = diff * unit_price_usd * exchange_rate
                shrinkage = round(shrinkage, 2)

        # 净利润 = (销售净额 - 业务员提成) - 支出合计 - 账面损耗
        net_profit = (total_sales_net - total_commission) - total_expenses - shrinkage

        # 利润率
        profit_margin = None
        if total_purchase_cny > 0:
            profit_margin = round(net_profit / total_purchase_cny * 100, 2)

        items.append(BatchReportSummaryItem(
            batch_id=batch.id,
            batch_code=batch.batch_code,
            batch_name=batch.batch_name,
            batch_date=batch.batch_date,
            status=batch.status,
            invoice_count=len(invoice_ids),
            invoice_nos="&".join(invoice_nos),
            total_purchase_usd=round(total_purchase_usd, 2),
            total_purchase_cny=round(total_purchase_cny, 2),
            total_weight_kg=round(total_weight, 3),
            total_boxes=total_boxes,
            total_import_duty=round(total_import_duty, 2),
            total_import_vat=round(total_import_vat, 2),
            total_taxes=round(total_taxes, 2),
            total_clearance_cost=round(total_clearance, 2),
            exchange_rate=exchange_rate,
            total_exchange_payment=round(total_exchange_payment, 2),
            total_exchange_fee=round(total_exchange_fee, 2),
            total_sales_amount=round(total_sales_amount, 2),
            total_sales_net=round(total_sales_net, 2),
            total_sales_weight=round(total_sales_weight, 3),
            sales_count=len(sales_list),
            total_expenses=round(total_expenses, 2),
            shrinkage=shrinkage,
            net_profit=round(net_profit, 2),
            profit_margin=profit_margin,
            cumulative_profit=cumulative_profit_map.get(batch.id, Decimal("0")),
            is_locked=batch.is_locked or False,
        ))

    return BatchReportListResponse(total=total, items=items, skip=skip, limit=limit)


@router.post("/batch/{batch_id}/lock", response_model=dict)
async def lock_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """锁定/解锁批次 - 锁定后禁止修改批次相关所有数据，并级联锁定关联发票"""
    batch_result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = batch_result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    
    batch.is_locked = not batch.is_locked
    
    # 级联锁定/解锁关联的发票
    from app.models import ImportInvoice
    batch_invoice_result = await db.execute(
        select(ImportInvoice)
        .join(BatchInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
        .where(BatchInvoice.batch_id == batch_id)
    )
    associated_invoices = batch_invoice_result.scalars().all()
    for inv in associated_invoices:
        inv.is_locked = batch.is_locked
    
    await db.commit()
    
    return {
        "success": True,
        "batch_id": batch_id,
        "is_locked": batch.is_locked,
        "message": "批次已锁定" if batch.is_locked else "批次已解锁"
    }


@router.get("/batch/{batch_id}", response_model=BatchReportDetail)
async def get_batch_report(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """批次财报详情 - 指定批次的完整财务报告"""
    # 获取批次
    batch_result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = batch_result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")

    # 获取关联发票
    bi_result = await db.execute(
        select(BatchInvoice, ImportInvoice)
        .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
        .where(BatchInvoice.batch_id == batch_id)
    )
    bi_rows = bi_result.all()

    if not bi_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次没有关联发票")

    # 批次级销售
    sales_list = await _get_batch_sales(db, batch_id)

    total_purchase_usd = Decimal("0")
    total_weight = Decimal("0")
    total_boxes = 0

    total_import_duty = Decimal("0")
    total_import_vat = Decimal("0")
    total_clearance = Decimal("0")
    total_exchange_payment = Decimal("0")
    total_exchange_fee = Decimal("0")
    exchange_rate = None
    batch_exchange_applied = False  # 批次级购汇只计算一次

    # 清关费分项汇总
    customs_broker_name = None
    clearance_breakdown = {
        "customs_broker": None,
        "clearance_fee": Decimal("0"),
        "freight_fee": Decimal("0"),
        "inspection_fee": Decimal("0"),
        "quarantine_fee": Decimal("0"),
        "other_costs": Decimal("0"),
    }

    invoice_details: List[BatchReportInvoiceDetail] = []
    invoice_nos = []

    # 先计算批次总重量用于销售分配
    batch_total_weight = Decimal("0")
    invoice_weights = {}
    for bi, inv in bi_rows:
        prod_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
        )
        prods = prod_result.scalars().all()
        w = sum(_to_decimal(p.net_weight_kg) for p in prods)
        if w == 0:
            w = _to_decimal(inv.total_weight_kg)
        invoice_weights[inv.id] = w
        batch_total_weight += w

    for bi, inv in bi_rows:
        invoice_nos.append(inv.invoice_no)
        inv_weight = invoice_weights[inv.id]
        inv_boxes = sum(
            p.box_count or 0 for p in
            (await db.execute(select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id))).scalars().all()
        )
        if inv_boxes == 0:
            inv_boxes = inv.total_boxes or 0

        prod_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
        )
        prods = prod_result.scalars().all()
        inv_amount = sum(_to_decimal(p.total_amount) for p in prods)
        if inv_amount == 0:
            inv_amount = _to_decimal(inv.total_amount_usd)

        # 税费
        tax = await _get_invoice_taxes(db, inv.id)
        inv_duty = _to_decimal(tax.import_duty) if tax else Decimal("0")
        inv_vat = _to_decimal(tax.import_vat) if tax else Decimal("0")

        # 清关
        clearance = await _get_invoice_clearance(db, inv.id)
        inv_clearance = Decimal("0")
        if clearance:
            inv_clearance = (
                _to_decimal(clearance.clearance_fee) +
                _to_decimal(clearance.freight_fee) +
                _to_decimal(clearance.inspection_fee) +
                _to_decimal(clearance.quarantine_fee) +
                _to_decimal(clearance.other_costs)
            )
            clearance_breakdown["clearance_fee"] += _to_decimal(clearance.clearance_fee)
            clearance_breakdown["freight_fee"] += _to_decimal(clearance.freight_fee)
            clearance_breakdown["inspection_fee"] += _to_decimal(clearance.inspection_fee)
            clearance_breakdown["quarantine_fee"] += _to_decimal(clearance.quarantine_fee)
            clearance_breakdown["other_costs"] += _to_decimal(clearance.other_costs)
            if clearance.customs_broker and not customs_broker_name:
                customs_broker_name = clearance.customs_broker
                clearance_breakdown["customs_broker"] = customs_broker_name

        # 购汇
        ex = await _get_invoice_exchange(db, inv.id, batch_id)
        inv_exchange_payment = Decimal("0")
        inv_exchange_fee = Decimal("0")
        inv_exchange_rate = Decimal("0")
        if ex:
            if ex.invoice_id == inv.id:
                # 发票级别购汇记录
                inv_exchange_payment = _to_decimal(ex.amount_cny)
                inv_exchange_fee = _to_decimal(ex.fee_cny)
                inv_exchange_rate = _to_decimal(ex.exchange_rate)
            elif not batch_exchange_applied:
                # 批次级别购汇记录，只计算一次
                inv_exchange_payment = _to_decimal(ex.amount_cny)
                inv_exchange_fee = _to_decimal(ex.fee_cny)
                inv_exchange_rate = _to_decimal(ex.exchange_rate)
                batch_exchange_applied = True

        if exchange_rate is None or exchange_rate == 0:
            if inv_exchange_rate > 0:
                exchange_rate = inv_exchange_rate

        # 汇总
        total_purchase_usd += inv_amount
        total_weight += inv_weight
        total_boxes += inv_boxes
        total_import_duty += inv_duty
        total_import_vat += inv_vat
        total_clearance += inv_clearance
        total_exchange_payment += inv_exchange_payment
        total_exchange_fee += inv_exchange_fee

        # 发票级采购成本
        er = inv_exchange_rate if inv_exchange_rate > 0 else (exchange_rate if exchange_rate else Decimal("7.0"))
        inv_purchase_cny = inv_amount * er

        # 销售分配比例
        proportion = Decimal("1")
        if batch_total_weight > 0 and len(bi_rows) > 1:
            proportion = inv_weight / batch_total_weight

        # 分配销售
        inv_sales_net = Decimal("0")
        inv_sales_weight = Decimal("0")
        for sale in sales_list:
            inv_sales_net += _to_decimal(sale.net_amount) * proportion
            inv_sales_weight += _to_decimal(sale.weight_kg) * proportion

        # 发票级支出
        inv_expenses = inv_duty + inv_vat + inv_clearance + inv_exchange_payment + inv_exchange_fee

        # 损耗
        inv_shrinkage = Decimal("0")
        if inv_weight > 0 and inv_sales_weight > 0:
            diff = inv_weight - inv_sales_weight
            if diff > 0:
                unit_price_usd = inv_amount / inv_weight if inv_weight > 0 else Decimal("0")
                inv_shrinkage = diff * unit_price_usd * er
                inv_shrinkage = round(inv_shrinkage, 2)

        # 净利润
        inv_net_profit = inv_sales_net - inv_expenses - inv_shrinkage

        # 溯源信息
        pp = await db.execute(select(Company).where(Company.id == inv.processing_plant_id))
        pp_company = pp.scalar_one_or_none()
        ff = await db.execute(select(Company).where(Company.id == inv.fish_farm_id))
        ff_company = ff.scalar_one_or_none()

        # 组装产品明细
        product_items = [
            {
                "product_name": p.product_name,
                "product_spec": p.product_spec,
                "box_count": p.box_count or 0,
                "net_weight_kg": round(_to_decimal(p.net_weight_kg), 3),
                "unit_price": round(_to_decimal(p.unit_price), 4),
                "total_amount": round(_to_decimal(p.total_amount), 2),
            }
            for p in prods
        ]

        invoice_details.append(BatchReportInvoiceDetail(
            invoice_id=inv.id,
            invoice_no=inv.invoice_no,
            invoice_date=inv.invoice_date,
            processing_plant_name=await _get_company_name(db, inv.processing_plant_id),
            processing_plant_eu_code=pp_company.code if pp_company else None,
            processing_plant_customs_code=pp_company.registration_code if pp_company else None,
            processing_plant_coc_no=pp_company.coc_cert_no if pp_company else None,
            fish_farm_name=await _get_company_name(db, inv.fish_farm_id),
            fish_farm_ggn=ff_company.registration_code if ff_company else None,
            fish_farm_coc_no=ff_company.coc_cert_no if ff_company else None,
            fish_farm_area=ff_company.farming_area if ff_company else None,
            exporter_name=await _get_company_name(db, inv.exporter_id),
            total_amount_usd=round(inv_amount, 2),
            total_boxes=inv_boxes,
            total_weight_kg=round(inv_weight, 3),
            purchase_cost_cny=round(inv_purchase_cny, 2),
            import_duty=inv_duty,
            import_vat=inv_vat,
            clearance_cost=round(inv_clearance, 2),
            exchange_payment=round(inv_exchange_payment, 2),
            exchange_fee=round(inv_exchange_fee, 2),
            sales_net=round(inv_sales_net, 2),
            sales_weight=round(inv_sales_weight, 3),
            shrinkage=inv_shrinkage,
            net_profit=round(inv_net_profit, 2),
            products=product_items,
        ))

    # 默认汇率
    if exchange_rate is None or exchange_rate == 0:
        exchange_rate = Decimal("7.0")

    # 采购成本(CNY)
    total_purchase_cny = total_purchase_usd * exchange_rate

    # 销售汇总
    total_sales_amount = Decimal("0")
    total_sales_net = Decimal("0")
    total_sales_weight = Decimal("0")
    total_scan_fee = Decimal("0")
    total_rounding = Decimal("0")
    total_commission = Decimal("0")
    total_after_sales = Decimal("0")
    total_discount = Decimal("0")
    sales_count = 0

    sales_data = []
    
    # 从 CommissionRecord 表查询提成汇总
    if sales_list:
        sale_ids = [s.id for s in sales_list]
        commission_result = await db.execute(
            select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(sale_ids))
        )
        total_commission = _to_decimal(commission_result.scalar())
    
    for sale in sales_list:
        customer_name = await _get_company_name(db, sale.customer_id)
        total_sales_amount += _to_decimal(sale.gross_amount)
        total_sales_net += _to_decimal(sale.net_amount)
        total_sales_weight += _to_decimal(sale.weight_kg)
        total_scan_fee += _to_decimal(sale.scan_fee)
        total_rounding += _to_decimal(sale.rounding_adjustment)
        total_after_sales += _to_decimal(sale.after_sales_adjustment)
        total_discount += _to_decimal(sale.discount)
        sales_count += 1

        sales_data.append({
            "sale_date": sale.sale_date,
            "customer_name": customer_name,
            "spec": sale.spec,
            "box_count": sale.box_count,
            "weight_kg": _to_decimal(sale.weight_kg),
            "unit_price": _to_decimal(sale.unit_price),
            "gross_amount": _to_decimal(sale.gross_amount),
            "scan_fee": _to_decimal(sale.scan_fee),
            "rounding_adjustment": _to_decimal(sale.rounding_adjustment),
            "commission": _to_decimal(sale.commission),
            "after_sales_adjustment": _to_decimal(sale.after_sales_adjustment),
            "discount": _to_decimal(sale.discount),
            "net_amount": _to_decimal(sale.net_amount),
        })

    # 重新计算销售净额（不包含 commission）
    total_sales_net = (
        total_sales_amount
        - total_scan_fee
        - total_rounding
        - total_after_sales
        - total_discount
    )

    # 支出合计
    total_taxes = total_import_duty + total_import_vat
    total_expenses = total_taxes + total_clearance + total_exchange_payment + total_exchange_fee

    # 损耗
    shrinkage = Decimal("0")
    if total_weight > 0 and total_sales_weight > 0:
        diff = total_weight - total_sales_weight
        if diff > 0:
            unit_price_usd = total_purchase_usd / total_weight if total_weight > 0 else Decimal("0")
            shrinkage = diff * unit_price_usd * exchange_rate
            shrinkage = round(shrinkage, 2)

    # 净利润 = (销售净额 - 业务员提成) - 支出合计 - 账面损耗
    net_profit = (total_sales_net - total_commission) - total_expenses - shrinkage

    # 累计利润（按日期顺序累加到当前批次为止的已完成批次净利润之和）
    cumulative_profit = Decimal("0")
    completed_batches_result = await db.execute(
        select(Batch.id, Batch.batch_date)
        .join(BatchInvoice, BatchInvoice.batch_id == Batch.id)
        .join(ImportInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
        .where(ImportInvoice.exchange_status == ExchangeStatus.COMPLETED)
        .where(
            or_(
                Batch.batch_date < batch.batch_date,
                and_(Batch.batch_date == batch.batch_date, Batch.id <= batch.id)
            )
        )
        .distinct()
        .order_by(Batch.batch_date, Batch.id)
    )
    completed_batch_rows = completed_batches_result.all()
    for (cb_id, cb_date) in completed_batch_rows:
        cb_sales_result = await db.execute(
            select(WholeFishSale).where(WholeFishSale.batch_id == cb_id)
        )
        cb_sales_list = cb_sales_result.scalars().all()
        cb_sales_net = sum(_to_decimal(s.net_amount) for s in cb_sales_list)

        # 从 CommissionRecord 查询该批次的提成
        cb_sale_ids = [s.id for s in cb_sales_list]
        cb_commission = Decimal("0")
        if cb_sale_ids:
            cb_commission_result = await db.execute(
                select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(cb_sale_ids))
            )
            cb_commission = _to_decimal(cb_commission_result.scalar())

        cb_ex_result = await db.execute(
            select(ExchangeRecord).where(ExchangeRecord.batch_id == cb_id)
        )
        cb_ex_list = cb_ex_result.scalars().all()
        cb_ex_payment = sum(_to_decimal(e.amount_cny) for e in cb_ex_list)
        cb_ex_fee = sum(_to_decimal(e.fee_cny) for e in cb_ex_list)

        cb_bi_result = await db.execute(
            select(BatchInvoice).where(BatchInvoice.batch_id == cb_id)
        )
        cb_inv_ids = [bi.invoice_id for bi in cb_bi_result.scalars().all()]

        cb_taxes = Decimal("0")
        cb_clearance = Decimal("0")
        for cb_inv_id in cb_inv_ids:
            cb_tax = await _get_invoice_taxes(db, cb_inv_id)
            if cb_tax:
                cb_taxes += _to_decimal(cb_tax.import_vat) + _to_decimal(cb_tax.import_duty)
            cb_clearance_item = await _get_invoice_clearance(db, cb_inv_id)
            if cb_clearance_item:
                cb_clearance += (
                    _to_decimal(cb_clearance_item.clearance_fee) +
                    _to_decimal(cb_clearance_item.freight_fee) +
                    _to_decimal(cb_clearance_item.inspection_fee) +
                    _to_decimal(cb_clearance_item.quarantine_fee) +
                    _to_decimal(cb_clearance_item.other_costs)
                )

        cb_expenses = cb_ex_payment + cb_ex_fee + cb_taxes + cb_clearance
        
        # 损耗
        cb_shrinkage = Decimal("0")
        if cb_inv_ids:
            cb_prod_result = await db.execute(
                select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(cb_inv_ids))
            )
            cb_prods = cb_prod_result.scalars().all()
            cb_import_weight = sum(_to_decimal(p.net_weight_kg) for p in cb_prods)
            cb_sales_weight = sum(_to_decimal(s.weight_kg) for s in cb_sales_list)
            if cb_import_weight > cb_sales_weight and cb_sales_weight > 0:
                cb_diff = cb_import_weight - cb_sales_weight
                cb_rate = Decimal("7.0")
                if cb_ex_list and cb_ex_list[0].exchange_rate and cb_ex_list[0].exchange_rate > 0:
                    cb_rate = _to_decimal(cb_ex_list[0].exchange_rate)
                cb_import_amount = sum(_to_decimal(p.total_amount) for p in cb_prods)
                if cb_import_amount > 0 and cb_import_weight > 0:
                    cb_unit_price = cb_import_amount / cb_import_weight
                    cb_shrinkage = cb_diff * cb_unit_price * cb_rate
        
        cumulative_profit += (cb_sales_net - cb_commission) - cb_expenses - round(cb_shrinkage, 2)

    # 利润率
    profit_margin = None
    if total_purchase_cny > 0:
        profit_margin = round(net_profit / total_purchase_cny * 100, 2)

    return BatchReportDetail(
        batch_id=batch.id,
        batch_code=batch.batch_code,
        batch_name=batch.batch_name,
        batch_date=batch.batch_date,
        status=batch.status,
        invoice_count=len(invoice_details),
        invoice_nos="&".join(invoice_nos),
        total_purchase_usd=round(total_purchase_usd, 2),
        total_purchase_cny=round(total_purchase_cny, 2),
        total_weight_kg=round(total_weight, 3),
        total_boxes=total_boxes,
        total_import_duty=round(total_import_duty, 2),
        total_import_vat=round(total_import_vat, 2),
        total_taxes=round(total_taxes, 2),
        total_clearance_cost=round(total_clearance, 2),
        clearance_breakdown={k: (round(v, 2) if isinstance(v, (int, float, Decimal)) else v) for k, v in clearance_breakdown.items()},
        exchange_rate=exchange_rate,
        total_exchange_payment=round(total_exchange_payment, 2),
        total_exchange_fee=round(total_exchange_fee, 2),
        total_sales_amount=round(total_sales_amount, 2),
        total_sales_net=round(total_sales_net, 2),
        total_sales_weight=round(total_sales_weight, 3),
        total_scan_fee=round(total_scan_fee, 2),
        total_rounding=round(total_rounding, 2),
        total_commission=round(total_commission, 2),
        total_after_sales=round(total_after_sales, 2),
        total_discount=round(total_discount, 2),
        sales_count=sales_count,
        total_expenses=round(total_expenses, 2),
        shrinkage=shrinkage,
        net_profit=round(net_profit, 2),
        profit_margin=profit_margin,
        cumulative_profit=round(cumulative_profit, 2),
        is_locked=batch.is_locked or False,
        invoices=invoice_details,
        sales=sales_data,
    )


# ==================== 单票财报 ====================

@router.get("/invoices", response_model=InvoiceReportListResponse)
async def list_invoice_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=500),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """单票财报列表 - 所有发票的核心财务指标汇总"""
    # 获取发票总数
    count_result = await db.execute(select(func.count(ImportInvoice.id)))
    total = count_result.scalar() or 0

    # 获取发票列表
    invoice_result = await db.execute(
        select(ImportInvoice).order_by(ImportInvoice.invoice_date.desc()).offset(skip).limit(limit)
    )
    invoices = invoice_result.scalars().all()

    items: List[InvoiceReportSummaryItem] = []
    for inv in invoices:
        # 批次信息
        batch_id, batch_name, batch_code = await _get_invoice_batch_info(db, inv.id)

        # 产品汇总
        prod_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
        )
        prods = prod_result.scalars().all()
        total_weight = sum(_to_decimal(p.net_weight_kg) for p in prods)
        total_boxes = sum(p.box_count or 0 for p in prods)
        total_amount_usd = sum(_to_decimal(p.total_amount) for p in prods)
        if total_amount_usd == 0:
            total_amount_usd = _to_decimal(inv.total_amount_usd)
        if total_weight == 0:
            total_weight = _to_decimal(inv.total_weight_kg)
        if total_boxes == 0:
            total_boxes = inv.total_boxes or 0

        # 税费
        tax = await _get_invoice_taxes(db, inv.id)
        import_duty = _to_decimal(tax.import_duty) if tax else Decimal("0")
        import_vat = _to_decimal(tax.import_vat) if tax else Decimal("0")
        total_taxes = import_duty + import_vat

        # 清关
        clearance = await _get_invoice_clearance(db, inv.id)
        clearance_cost = Decimal("0")
        if clearance:
            clearance_cost = (
                _to_decimal(clearance.clearance_fee) +
                _to_decimal(clearance.freight_fee) +
                _to_decimal(clearance.inspection_fee) +
                _to_decimal(clearance.quarantine_fee) +
                _to_decimal(clearance.other_costs)
            )

        # 购汇
        ex = await _get_invoice_exchange(db, inv.id, batch_id)
        exchange_rate = _to_decimal(ex.exchange_rate) if ex else Decimal("0")
        exchange_payment = _to_decimal(ex.amount_cny) if ex else Decimal("0")
        exchange_fee = _to_decimal(ex.fee_cny) if ex else Decimal("0")

        if exchange_rate == 0 and inv.estimated_exchange_rate:
            exchange_rate = _to_decimal(inv.estimated_exchange_rate)
        if exchange_rate == 0:
            exchange_rate = Decimal("7.0")

        # 采购成本
        purchase_cost_cny = total_amount_usd * exchange_rate

        # 销售数据（批次级，按比例分配）
        sales_net = Decimal("0")
        sales_weight = Decimal("0")
        sales_count = 0

        if batch_id:
            sales_list = await _get_batch_sales(db, batch_id)
            # 获取批次总重量用于比例分配
            batch_bi_result = await db.execute(
                select(BatchInvoice, ImportInvoice)
                .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
                .where(BatchInvoice.batch_id == batch_id)
            )
            batch_rows = batch_bi_result.all()
            batch_total_weight = Decimal("0")
            for bbi, binv in batch_rows:
                bprod_result = await db.execute(
                    select(InvoiceProduct).where(InvoiceProduct.invoice_id == binv.id)
                )
                bprods = bprod_result.scalars().all()
                bw = sum(_to_decimal(p.net_weight_kg) for p in bprods)
                if bw == 0:
                    bw = _to_decimal(binv.total_weight_kg)
                batch_total_weight += bw

            proportion = Decimal("1")
            if batch_total_weight > 0 and len(batch_rows) > 1:
                proportion = total_weight / batch_total_weight

            for sale in sales_list:
                sales_net += _to_decimal(sale.net_amount) * proportion
                sales_weight += _to_decimal(sale.weight_kg) * proportion
                sales_count += 1

        # 支出
        total_expenses = total_taxes + clearance_cost + exchange_payment + exchange_fee

        # 损耗
        shrinkage = Decimal("0")
        if total_weight > 0 and sales_weight > 0:
            diff = total_weight - sales_weight
            if diff > 0:
                unit_price_usd = total_amount_usd / total_weight if total_weight > 0 else Decimal("0")
                shrinkage = diff * unit_price_usd * exchange_rate
                shrinkage = round(shrinkage, 2)

        # 净利润
        net_profit = sales_net - total_expenses - shrinkage

        # 利润率
        profit_margin = None
        if purchase_cost_cny > 0:
            profit_margin = round(net_profit / purchase_cost_cny * 100, 2)

        items.append(InvoiceReportSummaryItem(
            invoice_id=inv.id,
            invoice_no=inv.invoice_no,
            invoice_date=inv.invoice_date,
            processing_plant_name=await _get_company_name(db, inv.processing_plant_id),
            exporter_name=await _get_company_name(db, inv.exporter_id),
            supplier_name=await _get_company_name(db, inv.supplier_id),
            batch_name=batch_name,
            batch_code=batch_code,
            total_amount_usd=round(total_amount_usd, 2),
            purchase_cost_cny=round(purchase_cost_cny, 2),
            total_weight_kg=round(total_weight, 3),
            total_boxes=total_boxes,
            import_duty=import_duty,
            import_vat=import_vat,
            total_taxes=total_taxes,
            clearance_cost=round(clearance_cost, 2),
            exchange_rate=exchange_rate,
            exchange_payment=round(exchange_payment, 2),
            exchange_fee=round(exchange_fee, 2),
            sales_net=round(sales_net, 2),
            sales_weight=round(sales_weight, 3),
            sales_count=sales_count,
            total_expenses=round(total_expenses, 2),
            shrinkage=shrinkage,
            net_profit=round(net_profit, 2),
            profit_margin=profit_margin,
        ))

    return InvoiceReportListResponse(total=total, items=items, skip=skip, limit=limit)


@router.get("/invoice/{invoice_id}", response_model=InvoiceReportDetail)
async def get_invoice_report(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """单票财报详情 - 指定发票的完整财务报告"""
    # 获取发票
    inv_result = await db.execute(select(ImportInvoice).where(ImportInvoice.id == invoice_id))
    invoice = inv_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发票不存在")

    # 批次信息
    batch_id, batch_name, batch_code = await _get_invoice_batch_info(db, invoice.id)

    # 计算核心数据
    data = await _calculate_invoice_report_data(db, invoice, include_sales=True)

    # 计算累计利润（如果该发票属于某个批次）
    cumulative_profit = Decimal("0")
    if batch_id:
        batch = await db.get(Batch, batch_id)
        if batch:
            # 计算到该批次为止的累计利润（复用批次财报逻辑）
            completed_batches_result = await db.execute(
                select(Batch.id, Batch.batch_date)
                .join(BatchInvoice, BatchInvoice.batch_id == Batch.id)
                .join(ImportInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
                .where(ImportInvoice.exchange_status == ExchangeStatus.COMPLETED)
                .where(
                    or_(
                        Batch.batch_date < batch.batch_date,
                        and_(Batch.batch_date == batch.batch_date, Batch.id <= batch.id)
                    )
                )
                .distinct()
                .order_by(Batch.batch_date, Batch.id)
            )
            for (cb_id, cb_date) in completed_batches_result.all():
                cb_sales_result = await db.execute(
                    select(WholeFishSale).where(WholeFishSale.batch_id == cb_id)
                )
                cb_sales_list = cb_sales_result.scalars().all()
                cb_sales_net = sum(_to_decimal(s.net_amount) for s in cb_sales_list)

                cb_sale_ids = [s.id for s in cb_sales_list]
                cb_commission = Decimal("0")
                if cb_sale_ids:
                    cb_commission_result = await db.execute(
                        select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(cb_sale_ids))
                    )
                    cb_commission = _to_decimal(cb_commission_result.scalar())

                cb_ex_result = await db.execute(
                    select(ExchangeRecord).where(ExchangeRecord.batch_id == cb_id)
                )
                cb_ex_list = cb_ex_result.scalars().all()
                cb_ex_payment = sum(_to_decimal(e.amount_cny) for e in cb_ex_list)
                cb_ex_fee = sum(_to_decimal(e.fee_cny) for e in cb_ex_list)

                cb_bi_result = await db.execute(
                    select(BatchInvoice).where(BatchInvoice.batch_id == cb_id)
                )
                cb_inv_ids = [bi.invoice_id for bi in cb_bi_result.scalars().all()]

                cb_taxes = Decimal("0")
                cb_clearance = Decimal("0")
                for cb_inv_id in cb_inv_ids:
                    cb_tax = await _get_invoice_taxes(db, cb_inv_id)
                    if cb_tax:
                        cb_taxes += _to_decimal(cb_tax.import_vat) + _to_decimal(cb_tax.import_duty)
                    cb_clearance_item = await _get_invoice_clearance(db, cb_inv_id)
                    if cb_clearance_item:
                        cb_clearance += (
                            _to_decimal(cb_clearance_item.clearance_fee) +
                            _to_decimal(cb_clearance_item.freight_fee) +
                            _to_decimal(cb_clearance_item.inspection_fee) +
                            _to_decimal(cb_clearance_item.quarantine_fee) +
                            _to_decimal(cb_clearance_item.other_costs)
                        )

                cb_expenses = cb_ex_payment + cb_ex_fee + cb_taxes + cb_clearance

                cb_shrinkage = Decimal("0")
                if cb_inv_ids:
                    cb_prod_result = await db.execute(
                        select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(cb_inv_ids))
                    )
                    cb_prods = cb_prod_result.scalars().all()
                    cb_import_weight = sum(_to_decimal(p.net_weight_kg) for p in cb_prods)
                    cb_sales_weight = sum(_to_decimal(s.weight_kg) for s in cb_sales_list)
                    if cb_import_weight > cb_sales_weight and cb_sales_weight > 0:
                        cb_diff = cb_import_weight - cb_sales_weight
                        cb_rate = Decimal("7.0")
                        if cb_ex_list and cb_ex_list[0].exchange_rate and cb_ex_list[0].exchange_rate > 0:
                            cb_rate = _to_decimal(cb_ex_list[0].exchange_rate)
                        cb_import_amount = sum(_to_decimal(p.total_amount) for p in cb_prods)
                        if cb_import_amount > 0 and cb_import_weight > 0:
                            cb_unit_price = cb_import_amount / cb_import_weight
                            cb_shrinkage = cb_diff * cb_unit_price * cb_rate

                cumulative_profit += (cb_sales_net - cb_commission) - cb_expenses - round(cb_shrinkage, 2)

    # 溯源信息
    pp = await db.execute(select(Company).where(Company.id == invoice.processing_plant_id))
    pp_company = pp.scalar_one_or_none()
    ff = await db.execute(select(Company).where(Company.id == invoice.fish_farm_id))
    ff_company = ff.scalar_one_or_none()
    ex = await db.execute(select(Company).where(Company.id == invoice.exporter_id))
    _ = ex.scalar_one_or_none()  # exporter info reserved for future use
    sup = await db.execute(select(Company).where(Company.id == invoice.supplier_id))
    sup_company = sup.scalar_one_or_none()

    # 构建产品明细
    products = []
    for p in data["products"]:
        products.append(InvoiceProductDetail(
            product_name=p.product_name,
            product_spec=p.product_spec,
            box_count=p.box_count,
            net_weight_kg=_to_decimal(p.net_weight_kg),
            unit_price=_to_decimal(p.unit_price),
            total_amount=_to_decimal(p.total_amount),
        ))

    # 构建销售明细
    sales = []
    for s in data["sales_data"]:
        sales.append(InvoiceSaleDetail(
            sale_date=s["sale_date"],
            customer_name=s["customer_name"],
            spec=s["spec"],
            box_count=s["box_count"],
            weight_kg=s["weight_kg"],
            unit_price=s["unit_price"],
            gross_amount=s["gross_amount"],
            scan_fee=s["scan_fee"],
            rounding_adjustment=s["rounding_adjustment"],
            commission=s["commission"],
            after_sales_adjustment=s["after_sales_adjustment"],
            discount=s["discount"],
            net_amount=s["net_amount"],
        ))

    return InvoiceReportDetail(
        invoice_id=invoice.id,
        invoice_no=invoice.invoice_no,
        invoice_date=invoice.invoice_date,
        kill_date=invoice.kill_date,
        arrival_date=invoice.arrival_date,
        processing_plant_name=data["processing_plant_name"],
        processing_plant_eu_code=pp_company.code if pp_company else None,
        processing_plant_customs_code=pp_company.registration_code if pp_company else None,
        processing_plant_coc_no=pp_company.coc_cert_no if pp_company else None,
        fish_farm_name=await _get_company_name(db, invoice.fish_farm_id),
        fish_farm_ggn=ff_company.registration_code if ff_company else None,
        fish_farm_coc_no=ff_company.coc_cert_no if ff_company else None,
        fish_farm_area=ff_company.farming_area if ff_company else None,
        exporter_name=data["exporter_name"],
        supplier_name=sup_company.name if sup_company else None,
        awb_no=invoice.awb_no,
        gross_weight_kg=_to_decimal(invoice.gross_weight_kg),
        batch_name=batch_name,
        batch_code=batch_code,
        total_amount_usd=data["total_amount_usd"],
        purchase_cost_cny=data["purchase_cost_cny"],
        total_weight_kg=data["total_weight_kg"],
        total_boxes=data["total_boxes"],
        products=products,
        import_duty=data["import_duty"],
        import_vat=data["import_vat"],
        total_taxes=data["total_taxes"],
        clearance_cost=data["clearance_cost"],
        clearance_breakdown=data["clearance_breakdown"],
        exchange_rate=data["exchange_rate"],
        exchange_payment=data["exchange_payment"],
        exchange_fee=data["exchange_fee"],
        total_sales_amount=data["total_sales_amount"],
        total_sales_net=data["total_sales_net"],
        total_sales_weight=data["total_sales_weight"],
        total_scan_fee=data["total_scan_fee"],
        total_rounding=data["total_rounding"],
        total_commission=data["total_commission"],
        total_after_sales=data["total_after_sales"],
        total_discount=data["total_discount"],
        sales_count=data["sales_count"],
        sales=sales,
        total_expenses=data["total_expenses"],
        shrinkage=data["shrinkage"],
        net_profit=data["net_profit"],
        cumulative_profit=cumulative_profit,
        profit_margin=data["profit_margin"],
    )


# ==================== 应收款对账单 ====================

@router.get("/receivable-statements", response_model=ReceivableStatementResponse)
async def list_receivable_statements(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=500),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    应收款对账单 - 按客户汇总
    
    公式：
    - 期初欠款 = 截至start_date的销售净额 - 截至start_date的收款
    - 本期销售 = start_date到end_date的销售净额
    - 本期收款 = start_date到end_date的收款
    - 期末欠款 = 期初 + 本期销售 - 本期收款
    """
    # 获取所有客户（type = customer）
    customer_result = await db.execute(
        select(Company)
        .where(Company.type == "customer")
        .order_by(Company.name)
    )
    customers = customer_result.scalars().all()

    # 如果没有日期参数，默认本月
    from datetime import datetime as _dt
    today = _dt.now().date()
    if not start_date:
        start_date = today.replace(day=1).isoformat()
    if not end_date:
        end_date = today.isoformat()

    start = _dt.strptime(start_date, "%Y-%m-%d").date()
    end = _dt.strptime(end_date, "%Y-%m-%d").date()

    items: List[ReceivableStatementItem] = []
    total_receivable = Decimal("0")

    for customer in customers:
        # 该客户所有销售记录
        sales_result = await db.execute(
            select(WholeFishSale)
            .where(WholeFishSale.customer_id == customer.id)
            .order_by(WholeFishSale.sale_date)
        )
        all_sales = sales_result.scalars().all()

        # 该客户所有收款记录
        receipts_result = await db.execute(
            select(SalesReceipt)
            .join(WholeFishSale, SalesReceipt.sale_id == WholeFishSale.id)
            .where(WholeFishSale.customer_id == customer.id)
            .order_by(SalesReceipt.receipt_date)
        )
        all_receipts = receipts_result.scalars().all()

        if not all_sales and not all_receipts:
            continue

        # 期初：截至 start_date 之前（不含当天）
        opening_sales = sum(
            _to_decimal(s.net_amount)
            for s in all_sales
            if s.sale_date < start
        )
        opening_receipts = sum(
            _to_decimal(r.amount)
            for r in all_receipts
            if r.receipt_date < start
        )
        opening_balance = opening_sales - opening_receipts

        # 本期销售
        current_sales = sum(
            _to_decimal(s.net_amount)
            for s in all_sales
            if start <= s.sale_date <= end
        )

        # 本期收款
        current_receipts = sum(
            _to_decimal(r.amount)
            for r in all_receipts
            if start <= r.receipt_date <= end
        )

        # 本期售后调整（扣减）
        aftersales_result = await db.execute(
            select(AftersalesRecord)
            .join(WholeFishSale, AftersalesRecord.sale_id == WholeFishSale.id)
            .where(
                WholeFishSale.customer_id == customer.id,
                AftersalesRecord.record_date >= start,
                AftersalesRecord.record_date <= end,
            )
        )
        current_aftersales = sum(
            _to_decimal(a.amount)
            for a in aftersales_result.scalars().all()
        )

        # 期末欠款
        closing_balance = opening_balance + current_sales - current_receipts - current_aftersales

        # 明细
        details: List[ReceivableCustomerItem] = []
        # 期初余额行
        if opening_balance != 0:
            details.append(ReceivableCustomerItem(
                date=start,
                type="opening",
                description="期初欠款",
                debit=opening_balance if opening_balance > 0 else Decimal("0"),
                credit=abs(opening_balance) if opening_balance < 0 else Decimal("0"),
                balance=opening_balance,
            ))

        # 销售明细
        for sale in all_sales:
            if start <= sale.sale_date <= end:
                details.append(ReceivableCustomerItem(
                    date=sale.sale_date,
                    type="sale",
                    sale_no=sale.sale_no,
                    description=f"销售 {sale.spec or ''}",
                    debit=_to_decimal(sale.net_amount),
                    credit=Decimal("0"),
                    balance=Decimal("0"),
                ))

        # 收款明细
        for receipt in all_receipts:
            if start <= receipt.receipt_date <= end:
                details.append(ReceivableCustomerItem(
                    date=receipt.receipt_date,
                    type="receipt",
                    description=f"收款 ({receipt.payment_method})",
                    debit=Decimal("0"),
                    credit=_to_decimal(receipt.amount),
                    balance=Decimal("0"),
                ))

        # 重新计算累计余额
        running_balance = opening_balance
        for d in details:
            if d.type == "sale":
                running_balance += d.debit
            elif d.type == "receipt":
                running_balance -= d.credit
            d.balance = running_balance

        # 按日期排序
        details.sort(key=lambda x: (x.date, 0 if x.type == "opening" else (1 if x.type == "sale" else 2)))

        if closing_balance != 0 or current_sales != 0 or current_receipts != 0:
            items.append(ReceivableStatementItem(
                customer_id=customer.id,
                customer_name=customer.name,
                customer_code=customer.code,
                opening_balance=round(opening_balance, 2),
                current_sales=round(current_sales, 2),
                current_receipts=round(current_receipts, 2),
                current_aftersales=round(current_aftersales, 2),
                closing_balance=round(closing_balance, 2),
                details=details,
            ))
            total_receivable += closing_balance

    # 分页
    total = len(items)
    paginated = items[skip:skip + limit]

    return ReceivableStatementResponse(
        total=total,
        items=paginated,
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        total_receivable=round(total_receivable, 2),
    )


# ==================== 应付款对账单 ====================

@router.get("/payable-statements", response_model=PayableStatementResponse)
async def list_payable_statements(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=500),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    应付款对账单 - 按供应商/加工厂/出口商汇总
    
    公式：
    - 期初欠款 = 截至start_date的采购额 - 截至start_date的付款
    - 本期采购 = start_date到end_date的新发票金额（USD×汇率）
    - 本期费用 = 税费 + 清关费
    - 本期付款 = 购汇 + 其他付款
    - 期末欠款 = 期初 + 本期采购 + 本期费用 - 本期付款
    """
    from datetime import datetime as _dt
    today = _dt.now().date()
    if not start_date:
        start_date = today.replace(day=1).isoformat()
    if not end_date:
        end_date = today.isoformat()

    start = _dt.strptime(start_date, "%Y-%m-%d").date()
    end = _dt.strptime(end_date, "%Y-%m-%d").date()

    # 获取所有有采购发票关联的公司（不只是supplier，exporter也可能是收款方）
    from sqlalchemy import distinct
    invoice_company_result = await db.execute(
        select(distinct(ImportInvoice.supplier_id))
        .where(ImportInvoice.supplier_id.isnot(None))
    )
    supplier_ids = [r[0] for r in invoice_company_result.all() if r[0]]
    
    if not supplier_ids:
        return PayableStatementResponse(
            total=0, items=[], skip=skip, limit=limit,
            start_date=start_date, end_date=end_date, total_payable=Decimal("0"),
        )
    
    supplier_result = await db.execute(
        select(Company)
        .where(Company.id.in_(supplier_ids))
        .order_by(Company.name)
    )
    suppliers = supplier_result.scalars().all()

    items: List[PayableStatementItem] = []
    total_payable = Decimal("0")

    for supplier in suppliers:
        # 该供应商相关的发票（按 supplier_id 关联）
        invoice_result = await db.execute(
            select(ImportInvoice)
            .where(ImportInvoice.supplier_id == supplier.id)
            .order_by(ImportInvoice.invoice_date)
        )
        all_invoices = invoice_result.scalars().all()

        if not all_invoices:
            continue

        # 该供应商相关的购汇记录（通过发票关联）
        invoice_ids = [inv.id for inv in all_invoices]
        exchange_result = await db.execute(
            select(ExchangeRecord)
            .where(ExchangeRecord.invoice_id.in_(invoice_ids))
            .order_by(ExchangeRecord.exchange_date)
        )
        all_exchanges = exchange_result.scalars().all()

        # 判断币种：USD 供应商用美元记账，其他用人民币
        is_usd = (supplier.currency or "CNY") == "USD"

        # 期初：截至 start_date 之前
        opening_invoices = Decimal("0")
        for inv in all_invoices:
            if inv.invoice_date < start:
                prod_result = await db.execute(
                    select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
                )
                prods = prod_result.scalars().all()
                amount_usd = sum(_to_decimal(p.total_amount) for p in prods)
                if amount_usd == 0:
                    amount_usd = _to_decimal(inv.total_amount_usd)
                
                if is_usd:
                    # USD 供应商：直接用 USD 金额，不转换
                    opening_invoices += amount_usd
                else:
                    # CNY 供应商：按汇率转换为 CNY
                    ex = await _get_invoice_exchange(db, inv.id, None)
                    rate = _to_decimal(ex.exchange_rate) if ex else Decimal("7.0")
                    if rate == 0:
                        rate = Decimal("7.0")
                    opening_invoices += amount_usd * rate

        if is_usd:
            # USD 供应商：付款用 exchanged USD
            opening_payments = sum(
                _to_decimal(ex.amount_usd)
                for ex in all_exchanges
                if ex.exchange_date < start
            )
        else:
            # CNY 供应商：付款用 CNY
            opening_payments = sum(
                _to_decimal(ex.amount_cny)
                for ex in all_exchanges
                if ex.exchange_date < start
            )
        opening_balance = opening_invoices - opening_payments

        # 本期采购
        current_purchase = Decimal("0")
        current_expenses = Decimal("0")
        for inv in all_invoices:
            if start <= inv.invoice_date <= end:
                prod_result = await db.execute(
                    select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
                )
                prods = prod_result.scalars().all()
                amount_usd = sum(_to_decimal(p.total_amount) for p in prods)
                if amount_usd == 0:
                    amount_usd = _to_decimal(inv.total_amount_usd)
                
                if is_usd:
                    current_purchase += amount_usd
                else:
                    ex = await _get_invoice_exchange(db, inv.id, None)
                    rate = _to_decimal(ex.exchange_rate) if ex else Decimal("7.0")
                    if rate == 0:
                        rate = Decimal("7.0")
                    purchase_cny = amount_usd * rate
                    current_purchase += purchase_cny

                # 税费（CNY费用，只对CNY供应商计入应付款）
                tax = await _get_invoice_taxes(db, inv.id)
                if tax and not is_usd:
                    current_expenses += _to_decimal(tax.import_duty) + _to_decimal(tax.import_vat)

                # 清关费用：不再计入供应商应付款，单独按报关行汇总
                # （见下方 customs_broker_items 处理）

        # 本期付款
        if is_usd:
            current_payments = sum(
                _to_decimal(ex.amount_usd)
                for ex in all_exchanges
                if start <= ex.exchange_date <= end
            )
        else:
            current_payments = sum(
                _to_decimal(ex.amount_cny) + _to_decimal(ex.fee_cny)
                for ex in all_exchanges
                if start <= ex.exchange_date <= end
            )

        # 期末欠款
        closing_balance = opening_balance + current_purchase + current_expenses - current_payments

        # 明细
        details: List[PayableSupplierItem] = []
        currency_label = "USD" if is_usd else "CNY"
        
        if opening_balance != 0:
            details.append(PayableSupplierItem(
                date=start,
                type="opening",
                description=f"期初欠款 ({currency_label})",
                debit=opening_balance if opening_balance > 0 else Decimal("0"),
                credit=abs(opening_balance) if opening_balance < 0 else Decimal("0"),
                balance=opening_balance,
            ))

        for inv in all_invoices:
            if start <= inv.invoice_date <= end:
                prod_result = await db.execute(
                    select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
                )
                prods = prod_result.scalars().all()
                amount_usd = sum(_to_decimal(p.total_amount) for p in prods)
                if amount_usd == 0:
                    amount_usd = _to_decimal(inv.total_amount_usd)
                
                if is_usd:
                    debit = amount_usd
                    desc = f"采购 {amount_usd:,.2f} USD"
                else:
                    ex = await _get_invoice_exchange(db, inv.id, None)
                    rate = _to_decimal(ex.exchange_rate) if ex else Decimal("7.0")
                    if rate == 0:
                        rate = Decimal("7.0")
                    debit = amount_usd * rate
                    desc = f"采购 {amount_usd:,.2f} USD @ {rate}"

                details.append(PayableSupplierItem(
                    date=inv.invoice_date,
                    type="invoice",
                    invoice_no=inv.invoice_no,
                    description=desc,
                    debit=debit,
                    credit=Decimal("0"),
                    balance=Decimal("0"),
                ))

                # 税费（仅CNY供应商显示）
                tax = await _get_invoice_taxes(db, inv.id)
                if tax and (tax.import_duty or tax.import_vat) and not is_usd:
                    tax_total = _to_decimal(tax.import_duty) + _to_decimal(tax.import_vat)
                    details.append(PayableSupplierItem(
                        date=inv.invoice_date,
                        type="invoice",
                        description="进口税费",
                        debit=tax_total,
                        credit=Decimal("0"),
                        balance=Decimal("0"),
                    ))

                # 清关费用不再显示在供应商明细中（单独按报关行汇总）

        for ex in all_exchanges:
            if start <= ex.exchange_date <= end:
                if is_usd:
                    details.append(PayableSupplierItem(
                        date=ex.exchange_date,
                        type="exchange",
                        description=f"购汇付款 ({ex.amount_usd:,.2f} USD)",
                        debit=Decimal("0"),
                        credit=_to_decimal(ex.amount_usd),
                        balance=Decimal("0"),
                    ))
                else:
                    details.append(PayableSupplierItem(
                        date=ex.exchange_date,
                        type="exchange",
                        description="购汇付款",
                        debit=Decimal("0"),
                        credit=_to_decimal(ex.amount_cny) + _to_decimal(ex.fee_cny),
                        balance=Decimal("0"),
                    ))

        # 重新计算累计余额
        running_balance = opening_balance
        for d in details:
            if d.type in ["invoice", "opening"]:
                running_balance += d.debit
            elif d.type in ["exchange", "payment"]:
                running_balance -= d.credit
            d.balance = running_balance

        details.sort(key=lambda x: (x.date, 0 if x.type == "opening" else 1))

        if closing_balance != 0 or current_purchase != 0 or current_payments != 0:
            supplier_type = "supplier"
            items.append(PayableStatementItem(
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                supplier_type=supplier_type,
                supplier_code=supplier.code,
                opening_balance=round(opening_balance, 2),
                current_purchase=round(current_purchase, 2),
                current_expenses=round(current_expenses, 2),
                current_payments=round(current_payments, 2),
                closing_balance=round(closing_balance, 2),
                details=details,
            ))
            total_payable += closing_balance

    # 单独汇总报关行应付款（按报关行分组）
    from sqlalchemy import func as sa_func
    customs_broker_result = await db.execute(
        select(
            ClearanceCost.customs_broker_id,
            Company.name.label("broker_name"),
            sa_func.sum(ClearanceCost.total_cost).label("total")
        )
        .join(Company, ClearanceCost.customs_broker_id == Company.id)
        .where(ClearanceCost.cost_date >= start)
        .where(ClearanceCost.cost_date <= end)
        .where(ClearanceCost.customs_broker_id.isnot(None))
        .group_by(ClearanceCost.customs_broker_id, Company.name)
    )
    customs_broker_rows = customs_broker_result.all()
    
    for row in customs_broker_rows:
        broker_id = row.customs_broker_id
        broker_name = row.broker_name or "未知报关行"
        broker_total = _to_decimal(row.total) or Decimal("0")
        if broker_total <= 0:
            continue
        
        broker_details: List[PayableSupplierItem] = []
        
        # 获取明细
        clearance_details = await db.execute(
            select(ClearanceCost, ImportInvoice.invoice_no)
            .join(ImportInvoice, ClearanceCost.invoice_id == ImportInvoice.id)
            .where(ClearanceCost.cost_date >= start)
            .where(ClearanceCost.cost_date <= end)
            .where(ClearanceCost.customs_broker_id == broker_id)
            .order_by(ClearanceCost.cost_date)
        )
        
        for cc, inv_no in clearance_details.all():
            broker_details.append(PayableSupplierItem(
                date=cc.cost_date,
                type="invoice",
                invoice_no=inv_no,
                description="清关费用",
                debit=_to_decimal(cc.total_cost),
                credit=Decimal("0"),
                balance=Decimal("0"),
            ))
        
        # 重新计算累计余额
        running_balance = Decimal("0")
        for d in broker_details:
            running_balance += d.debit
            d.balance = running_balance
        
        items.append(PayableStatementItem(
            supplier_id=broker_id,
            supplier_name=broker_name,
            supplier_type="customs_broker",
            supplier_code=None,
            opening_balance=Decimal("0"),
            current_purchase=Decimal("0"),
            current_expenses=round(broker_total, 2),
            current_payments=Decimal("0"),
            closing_balance=round(broker_total, 2),
            details=broker_details,
        ))
        total_payable += broker_total

    total = len(items)
    paginated = items[skip:skip + limit]

    return PayableStatementResponse(
        total=total,
        items=paginated,
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        total_payable=round(total_payable, 2),
    )


# ==================== 三大财务报表 ====================

@router.get("/financial-statements", response_model=FinancialStatements)
async def get_financial_statements(
    period_type: str = Query("current_quarter"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    retail_revenue: Decimal = Query(Decimal("0")),
    retail_cost: Decimal = Query(Decimal("0")),
    db: AsyncSession = Depends(get_db),
):
    """
    三大财务报表：利润表、资产负债表、现金流量表
    
    参考 salmon-finance-v4 shareholder_report.py 实现
    """
    from datetime import datetime as _dt, timedelta

    today = _dt.now().date()
    year = today.year

    def _get_quarter_dates(y, q):
        sm = (q - 1) * 3 + 1
        em = q * 3
        sd = f"{y}-{sm:02d}-01"
        if em == 12:
            ed = f"{y}-12-31"
        else:
            nd = _dt(y, em + 1, 1)
            ed = (nd - timedelta(days=1)).strftime("%Y-%m-%d")
        return sd, ed

    def _get_half_year_dates(y, h):
        if h == 1:
            return f"{y}-01-01", f"{y}-06-30"
        return f"{y}-07-01", f"{y}-12-31"

    def _get_year_dates(y):
        return f"{y}-01-01", f"{y}-12-31"

    # 解析周期
    if period_type == "custom" and start_date and end_date:
        sd, ed = start_date, end_date
    elif period_type == "current_quarter":
        q = (today.month - 1) // 3 + 1
        sd, ed = _get_quarter_dates(year, q)
    elif period_type == "last_quarter":
        q = (today.month - 1) // 3
        if q == 0:
            q = 4
            year -= 1
        sd, ed = _get_quarter_dates(year, q)
    elif period_type == "first_half":
        sd, ed = _get_half_year_dates(year, 1)
    elif period_type == "second_half":
        sd, ed = _get_half_year_dates(year, 2)
    elif period_type == "current_year":
        sd, ed = _get_year_dates(year)
    elif period_type == "last_year":
        sd, ed = _get_year_dates(year - 1)
    else:
        sd = today.replace(day=1).isoformat()
        ed = today.isoformat()

    sdt = _dt.strptime(sd, "%Y-%m-%d").date()
    edt = _dt.strptime(ed, "%Y-%m-%d").date()

    period_label_map = {
        "current_quarter": "本季度",
        "last_quarter": "上季度",
        "first_half": "上半年",
        "second_half": "下半年",
        "current_year": "本年度",
        "last_year": "上年度",
        "custom": "自定义周期",
    }
    period_label = f"{period_label_map.get(period_type, '周期')} ({sd} ~ {ed})"

    # ========== 1. 获取所有已购汇批次（利润表用）==========
    exchange_batch_result = await db.execute(
        select(ExchangeRecord.batch_id)
        .where(ExchangeRecord.batch_id.isnot(None))
        .distinct()
    )
    purchased_batch_ids = [r[0] for r in exchange_batch_result.all() if r[0]]

    # ========== 2. 构建利润表 ==========
    total_sales_net = Decimal("0")
    total_sales_gross = Decimal("0")
    total_scan_fee = Decimal("0")
    total_rounding = Decimal("0")
    total_after_sales = Decimal("0")
    total_commission = Decimal("0")
    total_discount = Decimal("0")
    total_exchange_payment = Decimal("0")
    total_exchange_fee = Decimal("0")
    total_import_vat = Decimal("0")
    total_import_duty = Decimal("0")
    total_clearance = Decimal("0")
    total_shrinkage = Decimal("0")
    total_other = Decimal("0")

    for batch_id in purchased_batch_ids:
        # 销售汇总
        sales_result = await db.execute(
            select(WholeFishSale).where(WholeFishSale.batch_id == batch_id)
        )
        sales_list = sales_result.scalars().all()
        for sale in sales_list:
            total_sales_net += _to_decimal(sale.net_amount)
            total_sales_gross += _to_decimal(sale.gross_amount)
            total_scan_fee += _to_decimal(sale.scan_fee)
            total_rounding += _to_decimal(sale.rounding_adjustment)
            total_after_sales += _to_decimal(sale.after_sales_adjustment)
            total_commission += _to_decimal(sale.commission)
            total_discount += _to_decimal(sale.discount)

        # 购汇
        ex_result = await db.execute(
            select(ExchangeRecord)
            .where(ExchangeRecord.batch_id == batch_id)
            .order_by(ExchangeRecord.created_at.desc())
        )
        ex = ex_result.scalar_one_or_none()
        if ex:
            total_exchange_payment += _to_decimal(ex.amount_cny)
            total_exchange_fee += _to_decimal(ex.fee_cny)

        # 批次发票
        bi_result = await db.execute(
            select(BatchInvoice).where(BatchInvoice.batch_id == batch_id)
        )
        bi_rows = bi_result.scalars().all()
        invoice_ids = [bi.invoice_id for bi in bi_rows]

        # 税费
        for inv_id in invoice_ids:
            tax = await _get_invoice_taxes(db, inv_id)
            if tax:
                total_import_vat += _to_decimal(tax.import_vat)
                total_import_duty += _to_decimal(tax.import_duty)

            # 清关
            clearance = await _get_invoice_clearance(db, inv_id)
            if clearance:
                total_clearance += (
                    _to_decimal(clearance.clearance_fee) +
                    _to_decimal(clearance.freight_fee) +
                    _to_decimal(clearance.inspection_fee) +
                    _to_decimal(clearance.quarantine_fee) +
                    _to_decimal(clearance.other_costs)
                )

        # 损耗
        batch_result = await db.execute(select(Batch).where(Batch.id == batch_id))
        batch = batch_result.scalar_one_or_none()
        if batch:
            # 获取批次总重量
            prod_result = await db.execute(
                select(InvoiceProduct)
                .join(BatchInvoice, InvoiceProduct.invoice_id == BatchInvoice.invoice_id)
                .where(BatchInvoice.batch_id == batch_id)
            )
            prods = prod_result.scalars().all()
            import_weight = sum(_to_decimal(p.net_weight_kg) for p in prods)
            sales_weight = sum(_to_decimal(s.weight_kg) for s in sales_list)
            if import_weight > 0 and sales_weight > 0 and import_weight > sales_weight:
                diff = import_weight - sales_weight
                # 获取汇率
                rate = Decimal("7.0")
                ex_result = await db.execute(
                    select(ExchangeRecord).where(ExchangeRecord.batch_id == batch_id)
                )
                ex = ex_result.scalar_one_or_none()
                if ex and ex.exchange_rate and ex.exchange_rate > 0:
                    rate = _to_decimal(ex.exchange_rate)
                # 计算采购金额
                import_amount = sum(_to_decimal(p.total_amount) for p in prods)
                if import_amount > 0 and import_weight > 0:
                    unit_price_usd = import_amount / import_weight
                    total_shrinkage += diff * unit_price_usd * rate

    # 日常支出（周期内）
    transaction_result = await db.execute(
        select(TransactionRecord)
        .where(
            TransactionRecord.type == "expense",
            TransactionRecord.transaction_date >= sdt,
            TransactionRecord.transaction_date <= edt,
        )
    )
    daily_expenses = transaction_result.scalars().all()
    daily_expense_by_category: dict = {}
    for t in daily_expenses:
        cat = str(t.category)
        daily_expense_by_category[cat] = daily_expense_by_category.get(cat, Decimal("0")) + _to_decimal(t.amount)
    total_daily_expense = sum(daily_expense_by_category.values())

    # 利润表计算
    wholesale_revenue = total_sales_net
    total_revenue = wholesale_revenue + retail_revenue
    cogs = total_exchange_payment + total_exchange_fee + total_import_vat + total_import_duty + total_clearance + round(total_shrinkage, 2)
    sales_expenses = total_commission + total_scan_fee + total_rounding + total_after_sales + total_discount + total_other + retail_cost
    operating_profit = total_revenue - cogs - sales_expenses - total_daily_expense
    net_profit = operating_profit

    # 日常支出明细项
    daily_expense_items = []
    for cat, amount in sorted(daily_expense_by_category.items(), key=lambda x: -x[1]):
        if amount > 0:
            daily_expense_items.append(
                FinancialStatementItem(label=f"        {cat}", amount=round(amount, 2), indent=2, is_deduction=True)
            )

    income_items = [
        FinancialStatementItem(label="一、营业收入（预估）", amount=round(total_revenue, 2), is_header=True),
        FinancialStatementItem(label="    1. 整鱼批发销售收入", amount=round(wholesale_revenue, 2), indent=1),
        FinancialStatementItem(label="    2. 零售销售收入", amount=round(retail_revenue, 2), indent=1, note="手动输入" if retail_revenue > 0 else "待开发"),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="二、营业成本", amount=round(cogs, 2), is_header=True, is_deduction=True),
        FinancialStatementItem(label="    3. 减：进口成本", amount=round(cogs, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="        采购成本（购汇付款）", amount=round(total_exchange_payment, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        购汇手续费", amount=round(total_exchange_fee, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        进口增值税", amount=round(total_import_vat, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        进口关税", amount=round(total_import_duty, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        清关费及运费", amount=round(total_clearance, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        账面损耗", amount=round(total_shrinkage, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="三、销售费用", amount=round(sales_expenses, 2), is_header=True, is_deduction=True),
        FinancialStatementItem(label="    4. 减：销售相关费用", amount=round(sales_expenses, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="        业务员提成", amount=round(total_commission, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        扫码手续费", amount=round(total_scan_fee, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        抹零", amount=round(total_rounding, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        售后调整", amount=round(total_after_sales, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        折扣", amount=round(total_discount, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        其他支出（批次）", amount=round(total_other, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        零售销售成本", amount=round(retail_cost, 2), indent=2, is_deduction=True, note="手动输入" if retail_cost > 0 else "待开发"),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="四、日常经营支出", amount=round(total_daily_expense, 2), is_header=True, is_deduction=True),
        FinancialStatementItem(label="    5. 减：日常经营支出", amount=round(total_daily_expense, 2), indent=1, is_deduction=True, note=f"共{len(daily_expense_by_category)}项"),
        *daily_expense_items,
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="营业利润", amount=round(operating_profit, 2), is_header=True, is_highlight=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="净利润", amount=round(net_profit, 2), is_header=True, is_total=True),
    ]

    income_statement = IncomeStatement(
        title="利润表",
        subtitle="（未经审计）",
        items=income_items,
        summary={
            "wholesale_revenue": round(wholesale_revenue, 2),
            "retail_revenue": round(retail_revenue, 2),
            "total_revenue": round(total_revenue, 2),
            "cogs": round(cogs, 2),
            "sales_expenses": round(sales_expenses, 2),
            "daily_expenses": round(total_daily_expense, 2),
            "operating_profit": round(operating_profit, 2),
            "net_profit": round(net_profit, 2),
            "profit_margin": round(net_profit / total_revenue * 100, 2) if total_revenue > 0 else 0,
        }
    )

    # ========== 3. 构建资产负债表 ==========
    # 货币资金 = 银行账户期初 + 已收销售款 + 日常收入 - 日常支出 - 购汇支出 - 进口费用
    bank_result = await db.execute(select(BankAccount))
    banks = bank_result.scalars().all()
    opening_balance = sum(_to_decimal(b.opening_balance) for b in banks)

    # 已收销售净额（截至 end_date）
    paid_sales_result = await db.execute(
        select(func.sum(WholeFishSale.net_amount))
        .where(
            WholeFishSale.status.in_(["partial_paid", "fully_paid"]),
            WholeFishSale.sale_date <= edt,
        )
    )
    paid_sales = _to_decimal(paid_sales_result.scalar())

    # 日常收入（非期初，截至 end_date）
    daily_income_result = await db.execute(
        select(func.sum(TransactionRecord.amount))
        .where(
            TransactionRecord.type == "income",
            TransactionRecord.transaction_date <= edt,
        )
    )
    daily_income_total = _to_decimal(daily_income_result.scalar())

    # 日常支出（截至 end_date）
    daily_expense_result = await db.execute(
        select(func.sum(TransactionRecord.amount))
        .where(
            TransactionRecord.type == "expense",
            TransactionRecord.transaction_date <= edt,
        )
    )
    daily_expense_total = _to_decimal(daily_expense_result.scalar())

    # 购汇支出（含手续费）
    exchange_total_result = await db.execute(
        select(func.sum(ExchangeRecord.amount_cny + ExchangeRecord.fee_cny))
    )
    exchange_total = _to_decimal(exchange_total_result.scalar())

    # 进口费用
    import_fees_result = await db.execute(
        select(
            func.sum(ImportTax.import_vat + ImportTax.import_duty),
            func.sum(ClearanceCost.clearance_fee + ClearanceCost.freight_fee + ClearanceCost.inspection_fee + ClearanceCost.quarantine_fee + ClearanceCost.other_costs),
        )
    )
    row = import_fees_result.first()
    import_fees = _to_decimal(row[0] if row else 0) + _to_decimal(row[1] if row else 0)

    cash_balance = round(
        opening_balance + paid_sales + daily_income_total
        - daily_expense_total - exchange_total - import_fees
    , 2)

    # 应收账款 = 客户未付款的销售净额
    receivable_result = await db.execute(
        select(
            WholeFishSale.customer_id,
            func.sum(WholeFishSale.net_amount).label("total"),
            func.sum(WholeFishSale.paid_amount).label("paid"),
        )
        .where(WholeFishSale.sale_date <= edt)
        .group_by(WholeFishSale.customer_id)
    )
    customer_debts = []
    accounts_receivable = Decimal("0")
    for row in receivable_result.all():
        customer_id, total_net, paid = row
        unpaid = _to_decimal(total_net) - _to_decimal(paid)
        if unpaid > 0:
            cust_result = await db.execute(select(Company.name).where(Company.id == customer_id))
            cust_name = cust_result.scalar() or "未知客户"
            customer_debts.append({
                "customer_id": customer_id,
                "customer_name": cust_name,
                "total": round(_to_decimal(total_net), 2),
                "paid": round(_to_decimal(paid), 2),
                "unpaid": round(unpaid, 2),
            })
            accounts_receivable += unpaid

    # 存货 = 未报关发票金额 × 汇率7（简化）
    uncleared_result = await db.execute(
        select(ImportInvoice).where(ImportInvoice.customs_status != "cleared")
    )
    uncleared_invoices = uncleared_result.scalars().all()
    total_uncleared = Decimal("0")
    for inv in uncleared_invoices:
        prod_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
        )
        prods = prod_result.scalars().all()
        amount = sum(_to_decimal(p.total_amount) for p in prods)
        if amount == 0:
            amount = _to_decimal(inv.total_amount_usd)
        total_uncleared += amount
    inventory_value = round(total_uncleared * Decimal("7"), 2)

    # 应付账款 = 已清关但未购汇的发票金额 × 汇率7（简化）
    # 简化：使用所有未付清的发票
    unpaid_invoice_result = await db.execute(
        select(ImportInvoice).where(ImportInvoice.exchange_status != "completed")
    )
    unpaid_invoices = unpaid_invoice_result.scalars().all()
    total_owed = Decimal("0")
    for inv in unpaid_invoices:
        prod_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
        )
        prods = prod_result.scalars().all()
        amount = sum(_to_decimal(p.total_amount) for p in prods)
        if amount == 0:
            amount = _to_decimal(inv.total_amount_usd)
        total_owed += amount
    accounts_payable = round(total_owed * Decimal("7"), 2)

    # 累计利润
    cumulative_profit = Decimal("0")
    for batch_id in purchased_batch_ids:
        sales_result = await db.execute(
            select(WholeFishSale).where(WholeFishSale.batch_id == batch_id)
        )
        sales_list = sales_result.scalars().all()
        sales_net = sum(_to_decimal(s.net_amount) for s in sales_list)

        # 从 CommissionRecord 查询提成
        sale_ids = [s.id for s in sales_list]
        commission_amount = Decimal("0")
        if sale_ids:
            commission_result = await db.execute(
                select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(sale_ids))
            )
            commission_amount = _to_decimal(commission_result.scalar())

        ex_result = await db.execute(
            select(ExchangeRecord).where(ExchangeRecord.batch_id == batch_id)
        )
        ex = ex_result.scalar_one_or_none()
        ex_payment = _to_decimal(ex.amount_cny) if ex else Decimal("0")
        ex_fee = _to_decimal(ex.fee_cny) if ex else Decimal("0")

        bi_result = await db.execute(
            select(BatchInvoice).where(BatchInvoice.batch_id == batch_id)
        )
        invoice_ids = [bi.invoice_id for bi in bi_result.scalars().all()]

        taxes = Decimal("0")
        clearance_cost = Decimal("0")
        for inv_id in invoice_ids:
            tax = await _get_invoice_taxes(db, inv_id)
            if tax:
                taxes += _to_decimal(tax.import_vat) + _to_decimal(tax.import_duty)
            clearance = await _get_invoice_clearance(db, inv_id)
            if clearance:
                clearance_cost += (
                    _to_decimal(clearance.clearance_fee) +
                    _to_decimal(clearance.freight_fee) +
                    _to_decimal(clearance.inspection_fee) +
                    _to_decimal(clearance.quarantine_fee) +
                    _to_decimal(clearance.other_costs)
                )

        total_exp = ex_payment + ex_fee + taxes + clearance_cost
        # 损耗
        shrink = Decimal("0")
        if invoice_ids:
            prod_result = await db.execute(
                select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(invoice_ids))
            )
            prods = prod_result.scalars().all()
            import_weight = sum(_to_decimal(p.net_weight_kg) for p in prods)
            sales_weight = sum(_to_decimal(s.weight_kg) for s in sales_list)
            if import_weight > sales_weight and sales_weight > 0:
                diff = import_weight - sales_weight
                rate = Decimal("7.0")
                if ex and ex.exchange_rate and ex.exchange_rate > 0:
                    rate = _to_decimal(ex.exchange_rate)
                import_amount = sum(_to_decimal(p.total_amount) for p in prods)
                if import_amount > 0 and import_weight > 0:
                    unit_price = import_amount / import_weight
                    shrink = diff * unit_price * rate
        
        cumulative_profit += (sales_net - commission_amount) - total_exp - round(shrink, 2)

    total_assets = cash_balance + accounts_receivable + inventory_value
    total_liabilities = accounts_payable
    owners_equity = round(cumulative_profit, 2)
    balance_check = round(total_assets - total_liabilities - owners_equity, 2)

    balance_items = [
        FinancialStatementItem(label="资产", amount=None, is_section=True),
        FinancialStatementItem(label="流动资产：", amount=None, is_header=True),
        FinancialStatementItem(label="    货币资金", amount=cash_balance, indent=1),
        FinancialStatementItem(label="    应收账款", amount=round(accounts_receivable, 2), indent=1),
        FinancialStatementItem(label="    存货", amount=inventory_value, indent=1, note=f"未报关 · 按汇率7×${total_uncleared:,.2f}USD"),
        FinancialStatementItem(label="流动资产合计", amount=round(total_assets, 2), is_subtotal=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="资产总计", amount=round(total_assets, 2), is_total=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="负债", amount=None, is_section=True),
        FinancialStatementItem(label="    应付账款", amount=round(accounts_payable, 2), indent=1, note=f"未购汇 · 按汇率7×${total_owed:,.2f}USD"),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="累计利润", amount=owners_equity, indent=0, note="已购汇批次实现的利润"),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="当前系统状态", amount=round(total_assets - accounts_payable + cumulative_profit, 2), is_total=True, note="资产 - 应付 + 累计利润"),
    ]

    balance_sheet = BalanceSheet(
        title="资产负债表",
        subtitle="（未经审计）",
        items=balance_items,
        summary={
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "owners_equity": owners_equity,
            "cash_balance": cash_balance,
            "accounts_receivable": round(accounts_receivable, 2),
            "inventory_value": inventory_value,
            "accounts_payable": round(accounts_payable, 2),
            "cumulative_profit": owners_equity,
            "balance_check": balance_check,
        },
        customer_debts=sorted(customer_debts, key=lambda x: -x["unpaid"])[:5],
    )

    # ========== 4. 构建现金流量表 ==========
    # 周期内销售总额及扣减项
    period_sales_result = await db.execute(
        select(
            func.sum(WholeFishSale.gross_amount).label("total_sales"),
            func.sum(WholeFishSale.rounding_adjustment).label("total_rounding"),
            func.sum(WholeFishSale.scan_fee).label("total_scan_fee"),
            func.sum(WholeFishSale.after_sales_adjustment).label("total_after_sales"),
        )
        .where(
            WholeFishSale.sale_date >= sdt,
            WholeFishSale.sale_date <= edt,
        )
    )
    row = period_sales_result.first()
    cash_from_sales = round(
        _to_decimal(row[0] if row else 0)
        - _to_decimal(row[1] if row else 0)
        - _to_decimal(row[2] if row else 0)
        - _to_decimal(row[3] if row else 0)
    , 2)

    # 周期内日常收入
    cash_from_other_result = await db.execute(
        select(func.sum(TransactionRecord.amount))
        .where(
            TransactionRecord.type == "income",
            TransactionRecord.transaction_date >= sdt,
            TransactionRecord.transaction_date <= edt,
        )
    )
    cash_from_other = _to_decimal(cash_from_other_result.scalar())

    # 周期内购汇付款+手续费
    period_exchange_result = await db.execute(
        select(
            func.sum(ExchangeRecord.amount_cny).label("cash_for_purchase"),
            func.sum(ExchangeRecord.fee_cny).label("cash_for_exchange_fee"),
        )
        .where(
            ExchangeRecord.exchange_date >= sdt,
            ExchangeRecord.exchange_date <= edt,
        )
    )
    row = period_exchange_result.first()
    cash_for_purchase = _to_decimal(row[0] if row else 0)
    cash_for_exchange_fee = _to_decimal(row[1] if row else 0)

    # 周期内税费+清关
    period_tax_result = await db.execute(
        select(
            func.sum(ImportTax.import_vat + ImportTax.import_duty).label("tax_total"),
            func.sum(
                ClearanceCost.clearance_fee + ClearanceCost.freight_fee +
                ClearanceCost.inspection_fee + ClearanceCost.quarantine_fee +
                ClearanceCost.other_costs
            ).label("clearance_total"),
        )
        .join(ImportInvoice, ImportTax.invoice_id == ImportInvoice.id)
        .join(ClearanceCost, ClearanceCost.invoice_id == ImportInvoice.id)
        .where(
            ImportInvoice.invoice_date >= sdt,
            ImportInvoice.invoice_date <= edt,
        )
    )
    row = period_tax_result.first()
    cash_for_tax = _to_decimal(row[0] if row else 0) + _to_decimal(row[1] if row else 0)

    # 周期内日常支出
    cash_for_daily_result = await db.execute(
        select(func.sum(TransactionRecord.amount))
        .where(
            TransactionRecord.type == "expense",
            TransactionRecord.transaction_date >= sdt,
            TransactionRecord.transaction_date <= edt,
        )
    )
    cash_for_daily_expense = _to_decimal(cash_for_daily_result.scalar())

    operating_inflow = cash_from_sales + cash_from_other
    operating_outflow = cash_for_purchase + cash_for_exchange_fee + cash_for_tax + cash_for_daily_expense
    net_operating_cash = operating_inflow - operating_outflow

    cashflow_items = [
        FinancialStatementItem(label="一、经营活动产生的现金流量", amount=None, is_section=True),
        FinancialStatementItem(label="销售商品、提供劳务收到的现金", amount=round(cash_from_sales, 2), indent=1),
        FinancialStatementItem(label="收到的其他与经营活动有关的现金", amount=round(cash_from_other, 2), indent=1),
        FinancialStatementItem(label="现金流入小计", amount=round(operating_inflow, 2), is_subtotal=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="购买商品、接受劳务支付的现金", amount=round(cash_for_purchase, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="支付的手续费", amount=round(cash_for_exchange_fee, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="支付的各项税费", amount=round(cash_for_tax, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="支付的其他与经营活动有关的现金", amount=round(cash_for_daily_expense, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="现金流出小计", amount=round(operating_outflow, 2), is_subtotal=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="经营活动产生的现金流量净额", amount=round(net_operating_cash, 2), is_highlight=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="二、投资活动产生的现金流量", amount=None, is_section=True),
        FinancialStatementItem(label="投资活动现金流入", amount=0, indent=1),
        FinancialStatementItem(label="投资活动现金流出", amount=0, indent=1, is_deduction=True),
        FinancialStatementItem(label="投资活动产生的现金流量净额", amount=0, indent=0),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="三、筹资活动产生的现金流量", amount=None, is_section=True),
        FinancialStatementItem(label="筹资活动现金流入", amount=0, indent=1),
        FinancialStatementItem(label="筹资活动现金流出", amount=0, indent=1, is_deduction=True),
        FinancialStatementItem(label="筹资活动产生的现金流量净额", amount=0, indent=0),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="四、现金及现金等价物净增加额", amount=round(net_operating_cash, 2), is_total=True),
    ]

    cash_flow = CashFlowStatement(
        title="现金流量表",
        subtitle="（未经审计）",
        items=cashflow_items,
        summary={
            "operating_inflow": round(operating_inflow, 2),
            "operating_outflow": round(operating_outflow, 2),
            "net_operating_cash": round(net_operating_cash, 2),
            "cash_from_sales": round(cash_from_sales, 2),
            "cash_for_purchase": round(cash_for_purchase, 2),
            "cash_for_tax": round(cash_for_tax, 2),
            "cash_for_other": round(cash_for_daily_expense, 2),
        }
    )

    # ========== 5. 图表数据 ==========
    # 月度收入/支出/利润趋势
    from sqlalchemy import text
    monthly_revenue_result = await db.execute(
        text("""
            SELECT TO_CHAR(sale_date, 'YYYY-MM') AS month, SUM(net_amount) AS revenue
            FROM whole_fish_sales
            WHERE sale_date >= :start AND sale_date <= :end
            GROUP BY TO_CHAR(sale_date, 'YYYY-MM')
            ORDER BY TO_CHAR(sale_date, 'YYYY-MM')
        """),
        {"start": sdt, "end": edt}
    )
    monthly_revenue = {r[0]: _to_decimal(r[1]) for r in monthly_revenue_result.all()}

    monthly_exchange_result = await db.execute(
        text("""
            SELECT TO_CHAR(exchange_date, 'YYYY-MM') AS month, SUM(amount_cny + fee_cny) AS expense
            FROM exchange_records
            WHERE exchange_date >= :start AND exchange_date <= :end
            GROUP BY TO_CHAR(exchange_date, 'YYYY-MM')
            ORDER BY TO_CHAR(exchange_date, 'YYYY-MM')
        """),
        {"start": sdt, "end": edt}
    )
    monthly_expense_exchange = {r[0]: _to_decimal(r[1]) for r in monthly_exchange_result.all()}

    monthly_daily_expense_result = await db.execute(
        text("""
            SELECT TO_CHAR(transaction_date, 'YYYY-MM') AS month, SUM(amount) AS expense
            FROM transaction_records
            WHERE type = 'EXPENSE' AND transaction_date >= :start AND transaction_date <= :end
            GROUP BY TO_CHAR(transaction_date, 'YYYY-MM')
            ORDER BY TO_CHAR(transaction_date, 'YYYY-MM')
        """),
        {"start": sdt, "end": edt}
    )
    monthly_expense_daily = {r[0]: _to_decimal(r[1]) for r in monthly_daily_expense_result.all()}

    all_months = sorted(set(list(monthly_revenue.keys()) + list(monthly_expense_exchange.keys()) + list(monthly_expense_daily.keys())))
    trend_data = []
    for month in all_months:
        rev = monthly_revenue.get(month, Decimal("0"))
        exp_ex = monthly_expense_exchange.get(month, Decimal("0"))
        exp_da = monthly_expense_daily.get(month, Decimal("0"))
        exp = exp_ex + exp_da
        trend_data.append({
            "month": month,
            "revenue": round(rev, 2),
            "expense": round(exp, 2),
            "profit": round(rev - exp, 2),
        })

    # 费用结构
    expense_breakdown = {
        "购汇付款": round(total_exchange_payment, 2),
        "购汇手续费": round(total_exchange_fee, 2),
        "进口增值税": round(total_import_vat, 2),
        "进口关税": round(total_import_duty, 2),
        "清关运费": round(total_clearance, 2),
        "业务员提成": round(total_commission, 2),
        "账面损耗": round(total_shrinkage, 2),
    }
    for cat, amount in daily_expense_by_category.items():
        expense_breakdown[cat] = round(expense_breakdown.get(cat, Decimal("0")) + amount, 2)
    expense_breakdown = {k: v for k, v in expense_breakdown.items() if v > 0}

    # 客户收入占比
    customer_revenue_result = await db.execute(
        select(
            WholeFishSale.customer_id,
            func.sum(WholeFishSale.net_amount).label("amount"),
        )
        .where(WholeFishSale.sale_date >= sdt, WholeFishSale.sale_date <= edt)
        .group_by(WholeFishSale.customer_id)
        .order_by(func.sum(WholeFishSale.net_amount).desc())
    )
    customer_revenue = []
    for row in customer_revenue_result.all():
        cid, amount = row
        if amount and amount > 0:
            cust_result = await db.execute(select(Company.name).where(Company.id == cid))
            name = cust_result.scalar() or "未命名客户"
            customer_revenue.append({"name": name, "value": round(_to_decimal(amount), 2)})

    # 利润走势
    cumulative = Decimal("0")
    profit_trend = []
    for t in trend_data:
        cumulative += Decimal(str(t["profit"]))
        profit_trend.append({
            "month": t["month"],
            "profit": t["profit"],
            "cumulative": round(cumulative, 2),
        })

    charts = FinancialCharts(
        monthly_trend=trend_data,
        expense_breakdown=expense_breakdown,
        customer_revenue=customer_revenue,
        profit_trend=profit_trend,
    )

    # 元信息
    meta = {
        "period_type": period_type,
        "period_label": period_label,
        "start_date": sd,
        "end_date": ed,
        "generated_at": _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company_name": "浙江中挪进出口有限公司",
        "company_name_en": "Zhejiang China-Norway Import & Export Co., Ltd.",
        "currency": "人民币（元）",
        "currency_en": "CNY (RMB)",
    }

    return FinancialStatements(
        meta=meta,
        income_statement=income_statement,
        balance_sheet=balance_sheet,
        cash_flow=cash_flow,
        charts=charts,
    )
