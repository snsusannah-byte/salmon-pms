"""
报表中心 - 批次财报 & 单票财报
"""
import csv
import io
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    AftersalesRecord,
    BankAccount,
    Batch,
    BatchInvoice,
    ClearanceCost,
    CommissionRecord,
    Company,
    ExchangeRecord,
    ExchangeStatus,
    FinishedProductAftersales,
    FinishedProductReceipt,
    FinishedProductSale,
    FinishedProductSaleV2,
    ImportInvoice,
    ImportTax,
    InvoiceProduct,
    MaterialPurchaseOrder,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderV2,
    PurchaseReturnOrder,
    ReturnItem,
    ReturnOrder,
    SalesReceipt,
    TransactionRecord,
    WholeFishSale,
)
from app.schemas.report import (
    BalanceSheet,
    BatchReportDetail,
    BatchReportInvoiceDetail,
    BatchReportListResponse,
    BatchReportSummaryItem,
    CashFlowStatement,
    FinancialCharts,
    FinancialStatementItem,
    FinancialStatements,
    IncomeStatement,
    InvoiceProductDetail,
    InvoiceReportDetail,
    InvoiceReportListResponse,
    InvoiceReportSummaryItem,
    InvoiceSaleDetail,
    NettingPaymentItem,
    NettingStatementItem,
    NettingStatementResponse,
    PayableExchangeItem,
    PayableExpenseItem,
    PayableMonthlyItem,
    PayableMonthlyResponse,
    PayablePaymentItem,
    PayablePurchaseItem,
    PayableStatementItem,
    PayableStatementResponse,
    PayableSupplierItem,
    CustomsBrokerStatementResponse,
    ReceivableAftersalesItem,
    ReceivableCustomerItem,
    ReceivableDiscountItem,
    ReceivableReceiptItem,
    ReceivableSaleItem,
    ReceivableStatementItem,
    ReceivableStatementResponse,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ==================== 辅助计算函数 ====================

async def _get_batch_sales(db: AsyncSession, batch_id: int) -> list[WholeFishSale]:
    """获取批次的所有销售记录"""
    result = await db.execute(
        select(WholeFishSale).where(WholeFishSale.batch_id == batch_id)
    )
    return result.scalars().all()


async def _get_invoice_taxes(db: AsyncSession, invoice_id: int) -> ImportTax | None:
    """获取发票的税费记录"""
    result = await db.execute(
        select(ImportTax).where(ImportTax.invoice_id == invoice_id)
    )
    return result.scalar_one_or_none()


async def _get_invoice_clearance(db: AsyncSession, invoice_id: int) -> ClearanceCost | None:
    """获取发票的清关费用记录"""
    result = await db.execute(
        select(ClearanceCost).where(ClearanceCost.invoice_id == invoice_id)
    )
    return result.scalar_one_or_none()


async def _batch_get_taxes(db: AsyncSession, invoice_ids: list[int]) -> dict[int, ImportTax | None]:
    """批量获取发票税费记录 - 替代循环内多次单查"""
    if not invoice_ids:
        return {}
    result = await db.execute(
        select(ImportTax).where(ImportTax.invoice_id.in_(invoice_ids))
    )
    return {t.invoice_id: t for t in result.scalars().all()}


async def _batch_get_clearances(db: AsyncSession, invoice_ids: list[int]) -> dict[int, ClearanceCost | None]:
    """批量获取发票清关费用记录 - 替代循环内多次单查"""
    if not invoice_ids:
        return {}
    result = await db.execute(
        select(ClearanceCost).where(ClearanceCost.invoice_id.in_(invoice_ids))
    )
    return {c.invoice_id: c for c in result.scalars().all()}


async def _batch_get_company_names(db: AsyncSession, company_ids: list[int]) -> dict[int, str]:
    """批量获取公司名称 - 替代循环内多次单查"""
    if not company_ids:
        return {}
    result = await db.execute(
        select(Company.id, Company.name).where(Company.id.in_(company_ids))
    )
    return {row[0]: row[1] for row in result.all() if row[0]}


# ─────────── 购汇估算（仅用于批次财报展示） ───────────
def _estimate_exchange(
    total_purchase_usd: Decimal,
    total_exchange_payment: Decimal,
    total_exchange_fee: Decimal,
    exchange_rate: Decimal | None = None,
) -> tuple[Decimal, Decimal, Decimal, Decimal | None, bool]:
    """对未购汇的批次做估算：汇率=6.8，手续费=150+0.1%×CNY。"""
    if total_exchange_payment > 0 or total_exchange_fee > 0:
        # 已有实际购汇数据，不做估算
        return total_purchase_usd, total_exchange_payment, total_exchange_fee, exchange_rate, False
    # 无购汇记录 → 估算
    estimated_rate = Decimal("6.8")
    estimated_payment = total_purchase_usd * estimated_rate
    estimated_fee = Decimal("150") + estimated_payment * Decimal("0.001")
    return total_purchase_usd, estimated_payment, estimated_fee, estimated_rate, True


async def _get_invoice_exchange(db: AsyncSession, invoice_id: int, batch_id: int | None = None) -> ExchangeRecord | None:
    """获取发票/批次的购汇记录（发票优先，回退到批次，最后查合并购汇的 related_invoice_ids）"""
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
        ex = result.scalar_one_or_none()
        if ex:
            return ex
    # 最后查合并购汇（通过 related_invoice_ids 包含当前发票ID）
    result = await db.execute(
        select(ExchangeRecord)
        .where(ExchangeRecord.related_invoice_ids.isnot(None))
        .order_by(ExchangeRecord.created_at.desc())
    )
    for ex in result.scalars().all():
        if ex.related_invoice_ids and invoice_id in ex.related_invoice_ids:
            return ex
    return None


async def _get_invoice_exchange_split(
    db: AsyncSession,
    invoice: ImportInvoice,
    batch_id: int | None = None,
) -> tuple:
    """
    【核心】获取发票的购汇分摊金额

    合并购汇场景：按当前发票 USD 金额占总购汇 USD 金额的比例分摊 CNY 金额
    单票/批次购汇场景：直接使用全额

    Returns:
        (exchange_payment, exchange_fee, exchange_rate, exchange_record)
    """
    exchange = await _get_invoice_exchange(db, invoice.id, batch_id)
    if not exchange:
        return Decimal("0"), Decimal("0"), Decimal("0"), None

    exchange_rate = _to_decimal(exchange.exchange_rate)

    # 判断是否合并购汇：related_invoice_ids 存在且包含当前发票
    is_merged_exchange = (
        exchange.related_invoice_ids
        and invoice.id in exchange.related_invoice_ids
    )

    if is_merged_exchange and exchange.amount_usd:
        # 合并购汇：按当前发票金额占总购汇金额的比例分摊
        total_exchange_usd = _to_decimal(exchange.amount_usd)
        invoice_amount_usd = _to_decimal(invoice.total_amount_usd)
        proportion = invoice_amount_usd / total_exchange_usd if total_exchange_usd > 0 else Decimal("0")

        exchange_payment = _to_decimal(exchange.amount_cny) * proportion
        exchange_fee = _to_decimal(exchange.fee_cny) * proportion
    else:
        # 单票/批次购汇：直接使用全额
        exchange_payment = _to_decimal(exchange.amount_cny)
        exchange_fee = _to_decimal(exchange.fee_cny)

    return exchange_payment, exchange_fee, exchange_rate, exchange


async def _get_company_name(db: AsyncSession, company_id: int | None) -> str | None:
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


async def _calc_batch_shrinkage(
    db: AsyncSession,
    batch_id: int,
    invoice_ids: list[int],
    sales_list: list[WholeFishSale],
) -> Decimal:
    """
    统一计算批次的账面损耗

    公式：(进口重量 - 销售重量) × 单价(USD) × 汇率
    """
    if not invoice_ids or not sales_list:
        return Decimal("0")

    prod_result = await db.execute(
        select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(invoice_ids))
    )
    prods = prod_result.scalars().all()
    import_weight = sum(_to_decimal(p.net_weight_kg) for p in prods)
    sales_weight = sum(_to_decimal(s.weight_kg) for s in sales_list)

    if import_weight <= sales_weight or sales_weight <= 0:
        return Decimal("0")

    diff = import_weight - sales_weight

    # 获取汇率
    rate = Decimal("7.0")
    ex_result = await db.execute(
        select(ExchangeRecord).where(ExchangeRecord.batch_id == batch_id)
    )
    for ex in ex_result.scalars().all():
        if ex and ex.exchange_rate and ex.exchange_rate > 0:
            rate = _to_decimal(ex.exchange_rate)
            break

    import_amount = sum(_to_decimal(p.total_amount) for p in prods)
    if import_amount > 0 and import_weight > 0:
        unit_price_usd = import_amount / import_weight
        return round(diff * unit_price_usd * rate, 2)

    return Decimal("0")

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

    # 购汇（使用统一分摊函数）
    exchange_payment, exchange_fee, exchange_rate, exchange = await _get_invoice_exchange_split(db, invoice, batch_id)

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
    total_balance_adjustment = Decimal("0")
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
            total_balance_adjustment += _to_decimal(sale.balance_adjustment)
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
                "balance_adjustment": _to_decimal(sale.balance_adjustment),
                "net_amount": _to_decimal(sale.net_amount),
            })

        # 重新计算销售净额（基于 sale.net_amount 累加，与详情页保持一致）
        total_sales_net = sum(
            _to_decimal(sale.net_amount) for sale in sales_list
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
        "total_balance_adjustment": total_balance_adjustment,
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
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """批次财报列表 - 所有批次的核心财务指标汇总"""
    # 获取批次总数
    count_result = await db.execute(select(func.count(Batch.id)))
    total = count_result.scalar() or 0

    # 获取批次列表
    batch_result = await db.execute(
        select(Batch).order_by(Batch.batch_date.desc(), Batch.id.desc()).offset(skip).limit(limit)
    )
    batches = batch_result.scalars().all()

    # 预计算所有批次的累计利润（包含所有批次，不仅仅是 completed）
    cumulative_profit_map = {}
    running_cumulative = Decimal("0")

    all_batches_result = await db.execute(
        select(Batch.id, Batch.batch_date)
        .distinct()
        .order_by(Batch.batch_date, Batch.id)
    )
    all_batch_rows = all_batches_result.all()

    for (cb_id, cb_date) in all_batch_rows:
        cb_batch = await db.get(Batch, cb_id)
        if cb_batch:
            cb_data = await _calc_batch_financials(db, cb_batch)
            if cb_data:
                # 期初留存 = 前批次累计（不包含当前批次）
                cumulative_profit_map[cb_id] = round(running_cumulative, 2)
                running_cumulative += cb_data["net_profit"]

    items: list[BatchReportSummaryItem] = []
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
        is_exchange_estimated = False  # 是否有发票使用了估算值

        # 预加载所有关联发票的税费和清关（避免循环内N+1查询）
        all_inv_ids = [inv.id for _, inv in bi_rows]
        taxes_map = await _batch_get_taxes(db, all_inv_ids)
        clearances_map = await _batch_get_clearances(db, all_inv_ids)

        # 批次财报中从票不计算进口费用（不参与主票分摊）
        # 只有主票（parent_invoice_id 为 None）计算自己的进口费用
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

            # 税费：只有主票计算，从票不计算
            if not inv.parent_invoice_id:
                tax = taxes_map.get(inv.id)
                if tax:
                    total_import_duty += _to_decimal(tax.import_duty)
                    total_import_vat += _to_decimal(tax.import_vat)

            # 清关：只有主票计算，从票不计算
            if not inv.parent_invoice_id:
                clearance = clearances_map.get(inv.id)
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
            if ex and ex.amount_cny > 0:
                if exchange_rate is None or exchange_rate == 0:
                    exchange_rate = _to_decimal(ex.exchange_rate)
                if ex.invoice_id == inv.id:
                    # 发票级别购汇
                    total_exchange_payment += _to_decimal(ex.amount_cny)
                    total_exchange_fee += _to_decimal(ex.fee_cny)
                elif ex.related_invoice_ids and inv.id in ex.related_invoice_ids:
                    # 合并购汇：按当前发票金额占总购汇金额的比例分摊
                    total_exchange_usd = _to_decimal(ex.amount_usd)
                    if total_exchange_usd > 0:
                        proportion = inv_amount / total_exchange_usd
                        total_exchange_payment += _to_decimal(ex.amount_cny) * proportion
                        total_exchange_fee += _to_decimal(ex.fee_cny) * proportion
                elif not batch_exchange_applied_summary:
                    # 批次级别购汇，只计算一次
                    total_exchange_payment += _to_decimal(ex.amount_cny)
                    total_exchange_fee += _to_decimal(ex.fee_cny)
                    batch_exchange_applied_summary = True
            else:
                # 无购汇记录或空记录 → 按发票级别估算
                inv_rate = Decimal("6.8")
                inv_payment = inv_amount * inv_rate
                inv_fee = Decimal("150") / len(bi_rows) + inv_payment * Decimal("0.001")
                total_exchange_payment += inv_payment
                total_exchange_fee += inv_fee
                if exchange_rate is None or exchange_rate == 0:
                    exchange_rate = inv_rate
                is_exchange_estimated = True

        # 批次销售汇总
        sales_list = await _get_batch_sales(db, batch.id)
        total_sales_amount = Decimal("0")
        total_sales_net = Decimal("0")
        total_sales_weight = Decimal("0")

        for sale in sales_list:
            total_sales_amount += _to_decimal(sale.gross_amount)
            total_sales_weight += _to_decimal(sale.weight_kg)
            # 重新计算销售净额（排除 commission，因为提成单独列出）
            # 避免直接使用 sale.net_amount（可能因数据不一致导致差异）
            total_sales_net += (
                _to_decimal(sale.gross_amount)
                - _to_decimal(sale.scan_fee)
                - _to_decimal(sale.rounding_adjustment)
                - _to_decimal(sale.after_sales_adjustment)
                - _to_decimal(sale.discount)
                - _to_decimal(sale.balance_adjustment)
            )

        # 从 CommissionRecord 表查询提成（仅用于显示）
        sale_ids = [s.id for s in sales_list]
        total_commission = Decimal("0")
        if sale_ids:
            commission_result = await db.execute(
                select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(sale_ids))
            )
            total_commission = _to_decimal(commission_result.scalar())

        # 其他支出（通过交易流水关联到该批次发票的额外支出，排除清关费支付）
        total_other_expenses = Decimal("0")
        total_clearance_extra = Decimal("0")
        if invoice_ids:
            other_exp_result = await db.execute(
                select(TransactionRecord).where(
                    TransactionRecord.type == "expense",
                    TransactionRecord.related_invoice_id.in_(invoice_ids),
                )
            )
            for txn in other_exp_result.scalars().all():
                if txn.category == "clearance_payment":
                    total_clearance_extra += _to_decimal(txn.amount)
                else:
                    total_other_expenses += _to_decimal(txn.amount)

        # 清关费合计包含额外支出
        total_clearance += total_clearance_extra

        # 汇率默认值
        if exchange_rate is None or exchange_rate == 0:
            exchange_rate = Decimal("7.0")

        # 采购成本(CNY)
        total_purchase_cny = total_purchase_usd * exchange_rate

        # 支出合计
        total_taxes = total_import_duty + total_import_vat
        total_expenses = total_taxes + total_clearance + total_exchange_payment + total_exchange_fee + total_other_expenses

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
            total_other_expenses=round(total_other_expenses, 2),
            shrinkage=shrinkage,
            net_profit=round(net_profit, 2),
            profit_margin=profit_margin,
            cumulative_profit=cumulative_profit_map.get(batch.id, Decimal("0")),
            total_commission=round(total_commission, 2),
            is_locked=batch.is_locked or False,
            is_exchange_estimated=is_exchange_estimated,
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




async def _calc_batch_financials(db: AsyncSession, batch) -> dict:
    """
    计算批次的所有财务数据（从关联发票获取到净利润计算）

    Returns:
        dict containing all financial metrics for the batch
    """
    batch_id = batch.id

    # 获取关联发票
    bi_result = await db.execute(
        select(BatchInvoice, ImportInvoice)
        .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
        .where(BatchInvoice.batch_id == batch_id)
    )
    bi_rows = bi_result.all()

    if not bi_rows:
        return None

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
    is_exchange_estimated = False  # 标记是否使用了估算值

    # 清关费分项汇总
    customs_broker_name = None
    clearance_breakdown = {
        "customs_broker": None,
        "clearance_fee": Decimal("0"),
        "freight_fee": Decimal("0"),
        "inspection_fee": Decimal("0"),
        "quarantine_fee": Decimal("0"),
        "other_costs": Decimal("0"),
        "extra_expenses": Decimal("0"),
    }

    invoice_details: list[dict] = []
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

    # 预加载所有发票的税费和清关（避免N+1）
    all_inv_ids = [inv.id for _, inv in bi_rows]
    taxes_map = await _batch_get_taxes(db, all_inv_ids)
    clearances_map = await _batch_get_clearances(db, all_inv_ids)

    # 批次财报中从票不计算进口费用（不参与主票分摊）
    # 只有主票（parent_invoice_id 为 None）计算自己的进口费用

    # 预加载所有发票的产品（避免循环内多次查询）
    prods_map_result = await db.execute(
        select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(all_inv_ids))
    )
    prods_map = {}
    for p in prods_map_result.scalars().all():
        prods_map.setdefault(p.invoice_id, []).append(p)

    for bi, inv in bi_rows:
        invoice_nos.append(inv.invoice_no)
        inv_weight = invoice_weights[inv.id]
        prods = prods_map.get(inv.id, [])
        inv_boxes = sum(p.box_count or 0 for p in prods)
        if inv_boxes == 0:
            inv_boxes = inv.total_boxes or 0

        inv_amount = sum(_to_decimal(p.total_amount) for p in prods)
        if inv_amount == 0:
            inv_amount = _to_decimal(inv.total_amount_usd)

        # 税费：只有主票计算，从票不计算
        if not inv.parent_invoice_id:
            tax = taxes_map.get(inv.id)
            if tax:
                inv_duty = _to_decimal(tax.import_duty)
                inv_vat = _to_decimal(tax.import_vat)
            else:
                inv_duty = Decimal("0")
                inv_vat = Decimal("0")
        else:
            inv_duty = Decimal("0")
            inv_vat = Decimal("0")

        # 清关：只有主票计算，从票不计算
        inv_clearance = Decimal("0")
        if not inv.parent_invoice_id:
            clearance = clearances_map.get(inv.id)
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
        if ex and ex.amount_cny > 0:
            if ex.invoice_id == inv.id:
                # 发票级别购汇记录
                inv_exchange_payment = _to_decimal(ex.amount_cny)
                inv_exchange_fee = _to_decimal(ex.fee_cny)
                inv_exchange_rate = _to_decimal(ex.exchange_rate)
            elif ex.related_invoice_ids and inv.id in ex.related_invoice_ids:
                # 合并购汇：按当前发票金额占总购汇金额的比例分摊
                total_exchange_usd = _to_decimal(ex.amount_usd)
                if total_exchange_usd > 0:
                    proportion = inv_amount / total_exchange_usd
                    inv_exchange_payment = _to_decimal(ex.amount_cny) * proportion
                    inv_exchange_fee = _to_decimal(ex.fee_cny) * proportion
                    inv_exchange_rate = _to_decimal(ex.exchange_rate)
            elif not batch_exchange_applied:
                # 批次级别购汇记录，只计算一次
                inv_exchange_payment = _to_decimal(ex.amount_cny)
                inv_exchange_fee = _to_decimal(ex.fee_cny)
                inv_exchange_rate = _to_decimal(ex.exchange_rate)
                batch_exchange_applied = True
        else:
            # 无购汇记录或空记录 → 批次财报估算：汇率=6.8，手续费=150+0.1%×CNY
            inv_exchange_rate = Decimal("6.8")
            inv_exchange_payment = inv_amount * inv_exchange_rate
            inv_exchange_fee = Decimal("150") / len(bi_rows) + inv_exchange_payment * Decimal("0.001")
            is_exchange_estimated = True

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

        invoice_details.append({
            "invoice_id": inv.id,
            "invoice_no": inv.invoice_no,
            "invoice_date": inv.invoice_date,
            "processing_plant_name": await _get_company_name(db, inv.processing_plant_id),
            "processing_plant_eu_code": pp_company.code if pp_company else None,
            "processing_plant_customs_code": pp_company.registration_code if pp_company else None,
            "processing_plant_coc_no": pp_company.coc_cert_no if pp_company else None,
            "fish_farm_name": await _get_company_name(db, inv.fish_farm_id),
            "fish_farm_ggn": ff_company.registration_code if ff_company else None,
            "fish_farm_coc_no": ff_company.coc_cert_no if ff_company else None,
            "fish_farm_area": ff_company.farming_area if ff_company else None,
            "exporter_name": await _get_company_name(db, inv.exporter_id),
            "total_amount_usd": round(inv_amount, 2),
            "total_boxes": inv_boxes,
            "total_weight_kg": round(inv_weight, 3),
            "purchase_cost_cny": round(inv_purchase_cny, 2),
            "import_duty": inv_duty,
            "import_vat": inv_vat,
            "clearance_cost": round(inv_clearance, 2),
            "exchange_payment": round(inv_exchange_payment, 2),
            "exchange_fee": round(inv_exchange_fee, 2),
            "sales_net": round(inv_sales_net, 2),
            "sales_weight": round(inv_sales_weight, 3),
            "shrinkage": inv_shrinkage,
            "net_profit": round(inv_net_profit, 2),
            "products": product_items,
        })

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
    total_balance_adjustment = Decimal("0")
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
        total_balance_adjustment += _to_decimal(sale.balance_adjustment)
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
        - total_balance_adjustment
    )

    # 其他支出（通过交易流水关联到该批次发票的额外支出）
    other_expenses_data = []
    total_other_expenses = Decimal("0")
    total_clearance_extra = Decimal("0")  # 清关费额外支出（category == "clearance_payment"）
    clearance_extra_items = []
    if all_inv_ids:
        other_exp_result = await db.execute(
            select(TransactionRecord).where(
                TransactionRecord.type == "expense",
                TransactionRecord.related_invoice_id.in_(all_inv_ids),
            ).order_by(TransactionRecord.transaction_date.desc())
        )
        for txn in other_exp_result.scalars().all():
            if txn.category == "clearance_payment":
                total_clearance_extra += _to_decimal(txn.amount)
                clearance_extra_items.append({
                    "id": txn.id,
                    "date": str(txn.transaction_date) if txn.transaction_date else None,
                    "amount": round(_to_decimal(txn.amount), 2),
                    "counterparty_name": txn.counterparty_name,
                    "description": txn.description,
                    "reference_no": txn.reference_no,
                    "category": txn.category,
                })
            else:
                total_other_expenses += _to_decimal(txn.amount)
                other_expenses_data.append({
                    "id": txn.id,
                    "date": str(txn.transaction_date) if txn.transaction_date else None,
                    "amount": round(_to_decimal(txn.amount), 2),
                    "counterparty_name": txn.counterparty_name,
                    "description": txn.description,
                    "reference_no": txn.reference_no,
                    "category": txn.category,
                })

    # 清关费合计 = 报关行清关费 + 额外清关支出
    total_clearance += total_clearance_extra

    # 支出合计
    total_taxes = total_import_duty + total_import_vat
    total_expenses = total_taxes + total_clearance + total_exchange_payment + total_exchange_fee + total_other_expenses

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

    return {
        "bi_rows": bi_rows,
        "sales_list": sales_list,
        "all_inv_ids": all_inv_ids,
        "invoice_nos": invoice_nos,
        "invoice_details": invoice_details,
        "sales_data": sales_data,
        "other_expenses_data": other_expenses_data,
        "clearance_extra_items": clearance_extra_items,
        "total_purchase_usd": total_purchase_usd,
        "total_purchase_cny": total_purchase_cny,
        "total_weight": total_weight,
        "total_boxes": total_boxes,
        "total_import_duty": total_import_duty,
        "total_import_vat": total_import_vat,
        "total_taxes": total_taxes,
        "total_clearance": total_clearance,
        "clearance_breakdown": clearance_breakdown,
        "exchange_rate": exchange_rate,
        "total_exchange_payment": total_exchange_payment,
        "total_exchange_fee": total_exchange_fee,
        "total_sales_amount": total_sales_amount,
        "total_sales_net": total_sales_net,
        "total_sales_weight": total_sales_weight,
        "total_scan_fee": total_scan_fee,
        "total_rounding": total_rounding,
        "total_commission": total_commission,
        "total_after_sales": total_after_sales,
        "total_discount": total_discount,
        "total_balance_adjustment": total_balance_adjustment,
        "sales_count": sales_count,
        "total_other_expenses": total_other_expenses,
        "total_clearance_extra": total_clearance_extra,
        "total_expenses": total_expenses,
        "shrinkage": shrinkage,
        "net_profit": net_profit,
        "profit_margin": profit_margin,
        "is_exchange_estimated": is_exchange_estimated,
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

    data = await _calc_batch_financials(db, batch)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次没有关联发票")

    # Unpack for response assembly
    data["all_inv_ids"]
    invoice_nos = data["invoice_nos"]
    invoice_details_raw = data["invoice_details"]
    sales_data = data["sales_data"]
    other_expenses_data = data["other_expenses_data"]
    clearance_extra_items = data["clearance_extra_items"]
    total_purchase_usd = data["total_purchase_usd"]
    total_purchase_cny = data["total_purchase_cny"]
    total_weight = data["total_weight"]
    total_boxes = data["total_boxes"]
    total_import_duty = data["total_import_duty"]
    total_import_vat = data["total_import_vat"]
    total_taxes = data["total_taxes"]
    total_clearance = data["total_clearance"]
    clearance_breakdown = data["clearance_breakdown"]
    exchange_rate = data["exchange_rate"]
    total_exchange_payment = data["total_exchange_payment"]
    total_exchange_fee = data["total_exchange_fee"]
    total_sales_amount = data["total_sales_amount"]
    total_sales_net = data["total_sales_net"]
    total_sales_weight = data["total_sales_weight"]
    total_scan_fee = data["total_scan_fee"]
    total_rounding = data["total_rounding"]
    total_commission = data["total_commission"]
    total_after_sales = data["total_after_sales"]
    total_discount = data["total_discount"]
    total_balance_adjustment = data["total_balance_adjustment"]
    sales_count = data["sales_count"]
    total_other_expenses = data["total_other_expenses"]
    total_clearance_extra = data["total_clearance_extra"]
    total_expenses = data["total_expenses"]
    shrinkage = data["shrinkage"]
    net_profit = data["net_profit"]
    profit_margin = data["profit_margin"]
    is_exchange_estimated = data["is_exchange_estimated"]

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
                and_(Batch.batch_date == batch.batch_date, Batch.id < batch.id)
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

        # 批量预加载税费和清关（避免N+1）
        cb_taxes_map = await _batch_get_taxes(db, cb_inv_ids)
        cb_clearances_map = await _batch_get_clearances(db, cb_inv_ids)

        cb_taxes = Decimal("0")
        cb_clearance = Decimal("0")
        for cb_inv_id in cb_inv_ids:
            cb_tax = cb_taxes_map.get(cb_inv_id)
            if cb_tax:
                cb_taxes += _to_decimal(cb_tax.import_vat) + _to_decimal(cb_tax.import_duty)
            cb_clearance_item = cb_clearances_map.get(cb_inv_id)
            if cb_clearance_item:
                cb_clearance += (
                    _to_decimal(cb_clearance_item.clearance_fee) +
                    _to_decimal(cb_clearance_item.freight_fee) +
                    _to_decimal(cb_clearance_item.inspection_fee) +
                    _to_decimal(cb_clearance_item.quarantine_fee) +
                    _to_decimal(cb_clearance_item.other_costs)
                )

        # 其他支出
        cb_other_expenses = Decimal("0")
        if cb_inv_ids:
            cb_other_result = await db.execute(
                select(func.sum(TransactionRecord.amount)).where(
                    TransactionRecord.type == "expense",
                    TransactionRecord.related_invoice_id.in_(cb_inv_ids),
                )
            )
            cb_other_expenses = _to_decimal(cb_other_result.scalar())

        cb_expenses = cb_ex_payment + cb_ex_fee + cb_taxes + cb_clearance + cb_other_expenses

        # 业务员提成
        cb_commission = Decimal("0")
        cb_sale_ids = [s.id for s in cb_sales_list]
        if cb_sale_ids:
            cb_commission_result = await db.execute(
                select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(cb_sale_ids))
            )
            cb_commission = _to_decimal(cb_commission_result.scalar())
        cb_expenses += cb_commission

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

        cumulative_profit += cb_sales_net - cb_expenses - round(cb_shrinkage, 2)

    # 清关费额外支出
    clearance_breakdown["extra_expenses"] = total_clearance_extra

    return BatchReportDetail(
        batch_id=batch.id,
        batch_code=batch.batch_code,
        batch_name=batch.batch_name,
        batch_date=batch.batch_date,
        status=batch.status,
        invoice_count=len(invoice_details_raw),
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
        clearance_extra_items=[{
            "id": item["id"],
            "date": item["date"],
            "amount": item["amount"],
            "description": item.get("description", ""),
            "counterparty_name": item.get("counterparty_name", ""),
            "reference_no": item.get("reference_no", ""),
        } for item in clearance_extra_items],
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
        total_balance_adjustment=round(total_balance_adjustment, 2),
        sales_count=sales_count,
        total_expenses=round(total_expenses, 2),
        total_other_expenses=round(total_other_expenses, 2),
        shrinkage=shrinkage,
        net_profit=round(net_profit, 2),
        profit_margin=profit_margin,
        cumulative_profit=round(cumulative_profit, 2),
        is_locked=batch.is_locked or False,
        is_exchange_estimated=is_exchange_estimated,
        invoices=[BatchReportInvoiceDetail(**d) for d in invoice_details_raw],
        sales=sales_data,
        other_expenses=other_expenses_data,
    )


# ==================== 单票财报 ====================

@router.get("/invoices", response_model=InvoiceReportListResponse)
async def list_invoice_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=500),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
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

    # 预加载所有发票的产品、税费、清关（避免循环内N+1）
    all_inv_ids = [inv.id for inv in invoices]
    prods_map_result = await db.execute(
        select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(all_inv_ids))
    )
    prods_map = {}
    for p in prods_map_result.scalars().all():
        prods_map.setdefault(p.invoice_id, []).append(p)

    taxes_map = await _batch_get_taxes(db, all_inv_ids)
    clearances_map = await _batch_get_clearances(db, all_inv_ids)

    items: list[InvoiceReportSummaryItem] = []
    for inv in invoices:
        # 批次信息
        batch_id, batch_name, batch_code = await _get_invoice_batch_info(db, inv.id)

        # 产品汇总（从预加载字典获取）
        prods = prods_map.get(inv.id, [])
        total_weight = sum(_to_decimal(p.net_weight_kg) for p in prods)
        total_boxes = sum(p.box_count or 0 for p in prods)
        total_amount_usd = sum(_to_decimal(p.total_amount) for p in prods)
        if total_amount_usd == 0:
            total_amount_usd = _to_decimal(inv.total_amount_usd)
        if total_weight == 0:
            total_weight = _to_decimal(inv.total_weight_kg)
        if total_boxes == 0:
            total_boxes = inv.total_boxes or 0

        # 税费（从预加载字典获取）
        tax = taxes_map.get(inv.id)
        import_duty = _to_decimal(tax.import_duty) if tax else Decimal("0")
        import_vat = _to_decimal(tax.import_vat) if tax else Decimal("0")
        total_taxes = import_duty + import_vat

        # 清关（从预加载字典获取）
        clearance = clearances_map.get(inv.id)
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
                bprods = prods_map.get(binv.id, [])
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

    # 计算销售分摊比例（合并批次中按重量比例分摊）
    sales_proportion = Decimal("1")
    if batch_id:
        bi_result = await db.execute(
            select(BatchInvoice, ImportInvoice)
            .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
            .where(BatchInvoice.batch_id == batch_id)
        )
        bi_rows = bi_result.all()
        if len(bi_rows) > 1:
            # 合并批次：按重量比例分摊销售
            batch_total_weight = Decimal("0")
            for _, inv in bi_rows:
                prod_result = await db.execute(
                    select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
                )
                prods = prod_result.scalars().all()
                w = sum(_to_decimal(p.net_weight_kg) for p in prods)
                if w == 0:
                    w = _to_decimal(inv.total_weight_kg)
                batch_total_weight += w
            # 当前发票重量
            inv_prod_result = await db.execute(
                select(InvoiceProduct).where(InvoiceProduct.invoice_id == invoice.id)
            )
            inv_prods = inv_prod_result.scalars().all()
            inv_weight = sum(_to_decimal(p.net_weight_kg) for p in inv_prods)
            if inv_weight == 0:
                inv_weight = _to_decimal(invoice.total_weight_kg)
            if batch_total_weight > 0:
                sales_proportion = inv_weight / batch_total_weight

    # 计算核心数据
    data = await _calculate_invoice_report_data(db, invoice, include_sales=True, sales_proportion=sales_proportion)

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
                        and_(Batch.batch_date == batch.batch_date, Batch.id < batch.id)
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

                cumulative_profit += cb_sales_net - cb_expenses - round(cb_shrinkage, 2)

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
        sales_proportion=sales_proportion,
    )


# ==================== 应收款对账单 ====================

@router.get("/receivable-statements", response_model=ReceivableStatementResponse)
async def list_receivable_statements(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=500),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    customer_id: int | None = Query(None, description="按客户筛选"),
    db: AsyncSession = Depends(get_db),
):
    """
    应收款对账单 - 按客户汇总

    公式：
    - 期初欠款 = 截至start_date之前所有销售净额 - 所有收款
    - 本期销售 = start_date到end_date的销售净额
    - 本期收款 = start_date到end_date的收款
    - 期末欠款 = 期初 + 本期销售 - 本期收款

    支持客户筛选：不传customer_id则返回所有客户汇总
    不传日期则查询全部历史数据
    """
    from datetime import datetime as _dt

    def _txn_date(receipt):
        """优先使用交易流水日期，更准确（支持用户修改后同步）"""
        return receipt.transaction.transaction_date if receipt.transaction else receipt.receipt_date

    # 获取有销售记录的公司列表（不再限定 type == "customer"，支持既是供应商又是客户的场景）
    from sqlalchemy import distinct
    sale_company_ids_result = await db.execute(
        select(distinct(WholeFishSale.customer_id)).where(WholeFishSale.customer_id.isnot(None))
    )
    fp_sale_company_ids_result = await db.execute(
        select(distinct(FinishedProductSale.customer_id)).where(FinishedProductSale.customer_id.isnot(None))
    )
    # 以销定采 V2 销售单（按客户名称关联）
    fp_v2_sale_customers_result = await db.execute(
        select(distinct(FinishedProductSaleV2.customer)).where(FinishedProductSaleV2.customer.isnot(None))
    )
    fp_v2_customers = [r[0] for r in fp_v2_sale_customers_result.all() if r[0]]
    # 查询这些客户名称对应的公司ID
    fp_v2_company_ids = set()
    if fp_v2_customers:
        v2_company_result = await db.execute(
            select(Company.id).where(Company.name.in_(fp_v2_customers))
        )
        fp_v2_company_ids = set(r[0] for r in v2_company_result.all() if r[0])

    sale_company_ids = set(
        [r[0] for r in sale_company_ids_result.all() if r[0]] +
        [r[0] for r in fp_sale_company_ids_result.all() if r[0]] +
        list(fp_v2_company_ids)
    )

    if customer_id:
        customer_query = select(Company).where(Company.id == customer_id)
    elif sale_company_ids:
        customer_query = select(Company).where(Company.id.in_(sale_company_ids)).order_by(Company.name)
    else:
        customer_query = select(Company).where(Company.type == "customer").order_by(Company.name)
    customer_result = await db.execute(customer_query)
    customers = customer_result.scalars().all()

    # 日期处理：不传则查全部
    start = None
    end = None
    if start_date:
        start = _dt.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        end = _dt.strptime(end_date, "%Y-%m-%d").date()

    items: list[ReceivableStatementItem] = []
    total_receivable = Decimal("0")

    for customer in customers:
        # ========== 整鱼销售 ==========
        sales_result = await db.execute(
            select(WholeFishSale)
            .options(selectinload(WholeFishSale.items))
            .where(WholeFishSale.customer_id == customer.id)
            .order_by(WholeFishSale.sale_date)
        )
        all_wf_sales = sales_result.scalars().all()

        # 整鱼销售的批次名称、宰杀日期、加工厂EU编号
        wf_batch_ids = {s.batch_id for s in all_wf_sales if s.batch_id}
        wf_batch_map = {}
        wf_batch_extra = {}
        if wf_batch_ids:
            batch_result = await db.execute(select(Batch.id, Batch.batch_name).where(Batch.id.in_(wf_batch_ids)))
            wf_batch_map = {r[0]: r[1] for r in batch_result.all()}

            batch_extra_result = await db.execute(
                select(BatchInvoice.batch_id, ImportInvoice.kill_date, Company.code)
                .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
                .join(Company, ImportInvoice.processing_plant_id == Company.id, isouter=True)
                .where(BatchInvoice.batch_id.in_(wf_batch_ids))
            )
            batch_extra_raw = {}
            for batch_id, kill_date, plant_code in batch_extra_result.all():
                d = batch_extra_raw.setdefault(batch_id, {"kill_dates": [], "plant_codes": []})
                if kill_date:
                    d["kill_dates"].append(kill_date)
                if plant_code:
                    d["plant_codes"].append(plant_code)
            wf_batch_extra = {
                bid: {
                    "slaughter_date": min(d["kill_dates"]) if d["kill_dates"] else None,
                    "processing_plant_code": d["plant_codes"][0] if d["plant_codes"] else None,
                }
                for bid, d in batch_extra_raw.items()
            }

        # 成品销售
        fp_sales_result = await db.execute(
            select(FinishedProductSale)
            .where(FinishedProductSale.customer_id == customer.id)
            .order_by(FinishedProductSale.sale_date)
        )
        all_fp_sales = fp_sales_result.scalars().all()

        # 以销定采 V2 销售单（按客户名称匹配）
        fp_v2_sales_result = await db.execute(
            select(FinishedProductSaleV2)
            .options(selectinload(FinishedProductSaleV2.products))
            .where(FinishedProductSaleV2.customer == customer.name)
            .order_by(FinishedProductSaleV2.sale_date)
        )
        all_fp_v2_sales = fp_v2_sales_result.scalars().all()

        # 整鱼收款
        wf_receipts_result = await db.execute(
            select(SalesReceipt)
            .options(selectinload(SalesReceipt.transaction))
            .join(WholeFishSale, SalesReceipt.sale_id == WholeFishSale.id)
            .where(WholeFishSale.customer_id == customer.id)
            .order_by(SalesReceipt.receipt_date)
        )
        all_wf_receipts = wf_receipts_result.scalars().all()

        # 成品收款（旧版）
        fp_receipts_result = await db.execute(
            select(FinishedProductReceipt)
            .options(selectinload(FinishedProductReceipt.transaction))
            .join(FinishedProductSale, FinishedProductReceipt.sale_id == FinishedProductSale.id)
            .where(FinishedProductSale.customer_id == customer.id)
            .order_by(FinishedProductReceipt.receipt_date)
        )
        all_fp_receipts = fp_receipts_result.scalars().all()

        # 以销定采 V2 收款
        fp_v2_receipts_result = await db.execute(
            select(FinishedProductReceipt)
            .options(selectinload(FinishedProductReceipt.transaction))
            .join(FinishedProductSaleV2, FinishedProductReceipt.sale_v2_id == FinishedProductSaleV2.id)
            .where(FinishedProductSaleV2.customer == customer.name)
            .order_by(FinishedProductReceipt.receipt_date)
        )
        all_fp_v2_receipts = fp_v2_receipts_result.scalars().all()

        # 整鱼售后
        wf_aftersales_result = await db.execute(
            select(AftersalesRecord)
            .join(WholeFishSale, AftersalesRecord.sale_id == WholeFishSale.id)
            .where(WholeFishSale.customer_id == customer.id)
        )
        all_wf_aftersales = wf_aftersales_result.scalars().all()

        # 成品售后（旧版）
        fp_aftersales_result = await db.execute(
            select(FinishedProductAftersales)
            .join(FinishedProductSale, FinishedProductAftersales.sale_id == FinishedProductSale.id)
            .where(FinishedProductSale.customer_id == customer.id)
        )
        all_fp_aftersales = fp_aftersales_result.scalars().all()

        # 以销定采 V2 售后
        fp_v2_aftersales_result = await db.execute(
            select(FinishedProductAftersales)
            .join(FinishedProductSaleV2, FinishedProductAftersales.sale_id == FinishedProductSaleV2.id)
            .where(FinishedProductSaleV2.customer == customer.name)
        )
        all_fp_v2_aftersales = fp_v2_aftersales_result.scalars().all()

        # 退货退款（ReturnOrder）
        return_orders_result = await db.execute(
            select(ReturnOrder)
            .where(ReturnOrder.customer_id == customer.id)
            .where(ReturnOrder.status == "completed")
        )
        all_return_orders = return_orders_result.scalars().all()

        # 售后退款交易流水（提前查询，期初计算需要）
        refund_tx_result = await db.execute(
            select(TransactionRecord)
            .where(TransactionRecord.counterparty_id == customer.id)
            .where(TransactionRecord.type == "expense")
            .where(TransactionRecord.category == "sales_refund")
        )
        refund_txs = refund_tx_result.scalars().all()

        # 客户预付款交易流水（提前查询，期初计算需要）
        prepayment_tx_result = await db.execute(
            select(TransactionRecord)
            .where(TransactionRecord.counterparty_id == customer.id)
            .where(TransactionRecord.type == "income")
            .where(TransactionRecord.category == "customer_deposit")
            .where(TransactionRecord.is_confirmed.is_(True))
        )
        prepayment_txs = prepayment_tx_result.scalars().all()

        # 如果没有销售和收款数据，但有退款或预付款数据，仍然处理（客户可能只有退款/预付款记录）
        if not all_wf_sales and not all_fp_sales and not all_fp_v2_sales and not all_wf_receipts and not all_fp_receipts and not all_fp_v2_receipts and not refund_txs and not all_return_orders and not prepayment_txs:
            continue

        # ========== 期初欠款（截至start之前的应收余额）==========
        # 正确计算：期初之前的销售净额 - 期初之前的收款 + 期初之前的退款
        opening_balance = Decimal("0")
        if start:
            # 期初之前的销售净额
            for s in all_wf_sales:
                if s.sale_date < start:
                    opening_balance += _to_decimal(s.net_amount)
            for s in all_fp_sales:
                if s.sale_date < start:
                    opening_balance += _to_decimal(s.net_amount)
            for s in all_fp_v2_sales:
                if s.sale_date < start:
                    opening_balance += _to_decimal(s.net_amount)
            
            # 期初之前的收款（使用 _txn_date 优先取交易流水日期，合并收款去重）
            processed_opening_txns = set()
            for r in all_wf_receipts:
                if _txn_date(r) < start:
                    if r.transaction_id:
                        if r.transaction_id not in processed_opening_txns:
                            processed_opening_txns.add(r.transaction_id)
                            opening_balance -= _to_decimal(r.transaction.amount if r.transaction else r.amount)
                    else:
                        opening_balance -= _to_decimal(r.amount)
            for r in all_fp_receipts:
                if _txn_date(r) < start:
                    if r.transaction_id:
                        if r.transaction_id not in processed_opening_txns:
                            processed_opening_txns.add(r.transaction_id)
                            opening_balance -= _to_decimal(r.transaction.amount if r.transaction else r.amount)
                    else:
                        opening_balance -= _to_decimal(r.amount)
            for r in all_fp_v2_receipts:
                if _txn_date(r) < start:
                    if r.transaction_id:
                        if r.transaction_id not in processed_opening_txns:
                            processed_opening_txns.add(r.transaction_id)
                            opening_balance -= _to_decimal(r.transaction.amount if r.transaction else r.amount)
                    else:
                        opening_balance -= _to_decimal(r.amount)
            
            # 期初之前的预付款（预付款也冲减应收）
            for txn in prepayment_txs:
                if txn.transaction_date < start:
                    opening_balance -= _to_decimal(txn.amount)
            
            # 期初之前的退款（退款会增加应收，即减少已收）
            for tx in refund_txs:
                if tx.transaction_date < start:
                    opening_balance += _to_decimal(tx.amount)
            for r in all_return_orders:
                if r.return_date < start and r.refund_method and r.refund_method.value == "direct_refund":
                    # 已生成交易流水的退货退款在 refund_txs 中已统计，避免重复
                    if r.transaction_id:
                        continue
                    opening_balance += _to_decimal(r.refund_amount)

        # ========== 本期销售（期间内所有销售金额 gross_amount 合计）==========
        current_sales = Decimal("0")
        current_net_sales = Decimal("0")
        for s in all_wf_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                current_sales += _to_decimal(s.gross_amount)
                current_net_sales += _to_decimal(s.net_amount)
        for s in all_fp_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                current_sales += _to_decimal(s.gross_amount)
                current_net_sales += _to_decimal(s.net_amount)
        for s in all_fp_v2_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                current_sales += _to_decimal(s.total_amount)
                current_net_sales += _to_decimal(s.net_amount)

        # ========== 本期售后 ==========
        # after_sales_adjustment 是销售单金额调整，已包含在 net 中
        # 直接统计 after_sales_adjustment 作为售后展示
        current_aftersales = Decimal("0")
        for sale in all_wf_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.after_sales_adjustment and sale.after_sales_adjustment > 0:
                    current_aftersales += _to_decimal(sale.after_sales_adjustment)
        for sale in all_fp_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.after_sales_adjustment and sale.after_sales_adjustment > 0:
                    current_aftersales += _to_decimal(sale.after_sales_adjustment)
        for sale in all_fp_v2_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.after_sales_adjustment and sale.after_sales_adjustment > 0:
                    current_aftersales += _to_decimal(sale.after_sales_adjustment)

        # ========== 本期收款 ==========
        # 实际收款 = 所有 receipt（不含balance，合并收款去重） - 售后退款
        total_receipts = Decimal("0")
        processed_current_txns = set()
        for r in all_wf_receipts:
            if r.payment_method != 'balance' and (start is None or _txn_date(r) >= start) and (end is None or _txn_date(r) <= end):
                if r.transaction_id:
                    if r.transaction_id not in processed_current_txns:
                        processed_current_txns.add(r.transaction_id)
                        total_receipts += _to_decimal(r.transaction.amount if r.transaction else r.amount)
                else:
                    total_receipts += _to_decimal(r.amount)
        for r in all_fp_receipts:
            if r.payment_method != 'balance' and (start is None or _txn_date(r) >= start) and (end is None or _txn_date(r) <= end):
                if r.transaction_id:
                    if r.transaction_id not in processed_current_txns:
                        processed_current_txns.add(r.transaction_id)
                        total_receipts += _to_decimal(r.transaction.amount if r.transaction else r.amount)
                else:
                    total_receipts += _to_decimal(r.amount)
        for r in all_fp_v2_receipts:
            if r.payment_method != 'balance' and (start is None or _txn_date(r) >= start) and (end is None or _txn_date(r) <= end):
                if r.transaction_id:
                    if r.transaction_id not in processed_current_txns:
                        processed_current_txns.add(r.transaction_id)
                        total_receipts += _to_decimal(r.transaction.amount if r.transaction else r.amount)
                else:
                    total_receipts += _to_decimal(r.amount)

        # 售后退款（已提前查询 refund_txs）
        total_refunds = Decimal("0")
        for tx in refund_txs:
            if (start is None or tx.transaction_date >= start) and (end is None or tx.transaction_date <= end):
                total_refunds += _to_decimal(tx.amount)
        # ReturnOrder 的直接退款也计入退款（未走交易流水的情况）
        for r in all_return_orders:
            if (start is None or r.return_date >= start) and (end is None or r.return_date <= end):
                if r.refund_method and r.refund_method.value == "direct_refund":
                    # 已生成交易流水的退货退款在 refund_txs 中已统计，避免重复
                    if r.transaction_id:
                        continue
                    total_refunds += _to_decimal(r.refund_amount)

        # 预付款也计入本期收款（冲减应收）
        for txn in prepayment_txs:
            if (start is None or txn.transaction_date >= start) and (end is None or txn.transaction_date <= end):
                total_receipts += _to_decimal(txn.amount)

        current_receipts = total_receipts - total_refunds

        # ========== 本期折扣 ==========
        current_discount = Decimal("0")
        for sale in all_wf_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.discount and sale.discount > 0:
                    current_discount += _to_decimal(sale.discount)
                if sale.balance_adjustment:
                    current_discount += _to_decimal(sale.balance_adjustment)
        for sale in all_fp_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.discount and sale.discount > 0:
                    current_discount += _to_decimal(sale.discount)
        for sale in all_fp_v2_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.discount and sale.discount > 0:
                    current_discount += _to_decimal(sale.discount)
                if sale.balance_adjustment:
                    current_discount += _to_decimal(sale.balance_adjustment)

        # ========== 期末欠款（基于期初+本期净额-本期收款推导，不重新遍历所有单据）==========
        # 勾稽关系：期末 = 期初 + 本期净额 - 本期收款
        # 其中 after_sales_adjustment 和 discount 已包含在 net_amount 中
        closing_balance = opening_balance + current_net_sales - current_receipts

        # 验证勾稽关系：期末 ≈ 期初 + 本期销售 - 本期收款 - 本期售后 - 本期折扣
        # （允许微小差异，因为 after_sales_adjustment 已包含在 net 中，而 ReturnOrder 是额外的）

        # ========== 明细（兼容旧版）==========
        details: list[ReceivableCustomerItem] = []

        # 期初余额行
        if opening_balance != 0:
            details.append(ReceivableCustomerItem(
                date=start or (_dt.now().date() if not start_date else _dt.strptime(start_date, "%Y-%m-%d").date()),
                type="opening",
                description="期初欠款",
                debit=opening_balance if opening_balance > 0 else Decimal("0"),
                credit=abs(opening_balance) if opening_balance < 0 else Decimal("0"),
                balance=opening_balance,
            ))

        # 整鱼销售明细
        for sale in all_wf_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                details.append(ReceivableCustomerItem(
                    date=sale.sale_date,
                    type="sale_wf",
                    sale_no=sale.sale_no,
                    description=f"整鱼销售 {sale.spec or ''}",
                    debit=_to_decimal(sale.net_amount),
                    credit=Decimal("0"),
                    balance=Decimal("0"),
                    spec=sale.spec,
                    quantity=sale.box_count,
                    weight_kg=sale.weight_kg,
                    unit_price=sale.unit_price,
                    gross_amount=sale.gross_amount,
                ))
                # 折扣明细（如果存在折扣）
                if sale.discount and sale.discount > 0:
                    details.append(ReceivableCustomerItem(
                        date=sale.sale_date,
                        type="discount",
                        sale_no=sale.sale_no,
                        description="折扣",
                        debit=Decimal("0"),
                        credit=_to_decimal(sale.discount),
                        balance=Decimal("0"),
                        discount_amount=sale.discount,
                    ))

        # 成品销售明细
        for sale in all_fp_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                details.append(ReceivableCustomerItem(
                    date=sale.sale_date,
                    type="sale_fp",
                    sale_no=f"FP-{sale.id}",
                    description="成品销售",
                    debit=_to_decimal(sale.net_amount),
                    credit=Decimal("0"),
                    balance=Decimal("0"),
                    spec="成品",
                    quantity=sale.quantity,
                    weight_kg=sale.total_weight_kg,
                    unit_price=sale.unit_price,
                    gross_amount=sale.gross_amount,
                ))
                # 折扣明细（如果存在折扣）
                if sale.discount and sale.discount > 0:
                    details.append(ReceivableCustomerItem(
                        date=sale.sale_date,
                        type="discount",
                        sale_no=f"FP-{sale.id}",
                        description="折扣",
                        debit=Decimal("0"),
                        credit=_to_decimal(sale.discount),
                        balance=Decimal("0"),
                        discount_amount=sale.discount,
                    ))

        # 以销定采 V2 销售明细
        for sale in all_fp_v2_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                details.append(ReceivableCustomerItem(
                    date=sale.sale_date,
                    type="sale_fp",
                    sale_no=sale.sale_no,
                    description="以销定采销售",
                    debit=_to_decimal(sale.net_amount),
                    credit=Decimal("0"),
                    balance=Decimal("0"),
                    spec=sale.product_name or "成品",
                    quantity=sale.quantity,
                    weight_kg=sale.weight,
                    unit_price=sale.unit_price,
                    gross_amount=sale.total_amount,
                ))
                # 折扣明细（如果存在折扣）
                if sale.discount and sale.discount > 0:
                    details.append(ReceivableCustomerItem(
                        date=sale.sale_date,
                        type="discount",
                        sale_no=sale.sale_no,
                        description="折扣",
                        debit=Decimal("0"),
                        credit=_to_decimal(sale.discount),
                        balance=Decimal("0"),
                        discount_amount=sale.discount,
                    ))

        # 整鱼收款明细
        for receipt in all_wf_receipts:
            if (start is None or receipt.receipt_date >= start) and (end is None or receipt.receipt_date <= end):
                details.append(ReceivableCustomerItem(
                    date=receipt.receipt_date,
                    type="receipt_wf",
                    description=f"收款 ({receipt.payment_method})",
                    debit=Decimal("0"),
                    credit=_to_decimal(receipt.amount),
                    balance=Decimal("0"),
                ))

        # 成品收款明细（旧版）
        for receipt in all_fp_receipts:
            if (start is None or receipt.receipt_date >= start) and (end is None or receipt.receipt_date <= end):
                details.append(ReceivableCustomerItem(
                    date=receipt.receipt_date,
                    type="receipt_fp",
                    description=f"收款 ({receipt.payment_method})",
                    debit=Decimal("0"),
                    credit=_to_decimal(receipt.amount),
                    balance=Decimal("0"),
                ))

        # 以销定采 V2 收款明细
        for receipt in all_fp_v2_receipts:
            if (start is None or receipt.receipt_date >= start) and (end is None or receipt.receipt_date <= end):
                details.append(ReceivableCustomerItem(
                    date=receipt.receipt_date,
                    type="receipt_fp",
                    description=f"收款 ({receipt.payment_method})",
                    debit=Decimal("0"),
                    credit=_to_decimal(receipt.amount),
                    balance=Decimal("0"),
                ))

        # 售后扣减（旧版）
        for a in all_wf_aftersales:
            if (start is None or a.record_date >= start) and (end is None or a.record_date <= end):
                details.append(ReceivableCustomerItem(
                    date=a.record_date,
                    type="aftersales",
                    sale_no=None,
                    description=f"售后 {a.reason or ''}",
                    debit=Decimal("0"),
                    credit=_to_decimal(a.amount),
                    balance=Decimal("0"),
                    aftersales_reason=a.reason,
                ))
        for a in all_fp_aftersales:
            if (start is None or a.record_date >= start) and (end is None or a.record_date <= end):
                details.append(ReceivableCustomerItem(
                    date=a.record_date,
                    type="aftersales",
                    sale_no=None,
                    description=f"售后 {a.reason or ''}",
                    debit=Decimal("0"),
                    credit=_to_decimal(a.amount),
                    balance=Decimal("0"),
                    aftersales_reason=a.reason,
                ))
        # 以销定采 V2 售后
        for a in all_fp_v2_aftersales:
            if (start is None or a.record_date >= start) and (end is None or a.record_date <= end):
                details.append(ReceivableCustomerItem(
                    date=a.record_date,
                    type="aftersales",
                    sale_no=None,
                    description=f"售后 {a.reason or ''}",
                    debit=Decimal("0"),
                    credit=_to_decimal(a.amount),
                    balance=Decimal("0"),
                    aftersales_reason=a.reason,
                ))
        # 退货退款
        for r in all_return_orders:
            if (start is None or r.return_date >= start) and (end is None or r.return_date <= end):
                details.append(ReceivableCustomerItem(
                    date=r.return_date,
                    type="aftersales",
                    sale_no=r.return_no,
                    description=f"退货退款 ({r.refund_method.value if r.refund_method else 'unknown'})",
                    debit=Decimal("0"),
                    credit=_to_decimal(r.refund_amount),
                    balance=Decimal("0"),
                    aftersales_reason=r.problem_description,
                ))

        # 重新计算累计余额
        running_balance = opening_balance
        for d in details:
            if d.type in ("sale_wf", "sale_fp", "opening"):
                running_balance += d.debit
            elif d.type in ("receipt_wf", "receipt_fp", "aftersales", "discount"):
                running_balance -= d.credit
            d.balance = running_balance

        # 按日期排序
        details.sort(key=lambda x: (x.date, 0 if x.type == "opening" else (1 if x.type.startswith("sale") else 2)))

        # ========== 分组明细（新版）==========
        sale_details: list[ReceivableSaleItem] = []
        discount_details: list[ReceivableDiscountItem] = []
        aftersales_details: list[ReceivableAftersalesItem] = []
        receipt_details: list[ReceivableReceiptItem] = []

        # 销售明细
        for sale in all_wf_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                batch_extra = wf_batch_extra.get(sale.batch_id, {})
                wf_items = sale.items or []
                if wf_items:
                    total_gross = sum(_to_decimal(item.amount) for item in wf_items)
                    sale_net = _to_decimal(sale.net_amount)
                    net_ratio = sale_net / total_gross if total_gross else Decimal("0")
                    total_after = _to_decimal(sale.after_sales_adjustment)
                    total_discount = _to_decimal(sale.discount)
                    cumulative_net = Decimal("0")
                    for i, item in enumerate(wf_items):
                        item_amount = _to_decimal(item.amount)
                        if i == len(wf_items) - 1:
                            item_net = sale_net - cumulative_net
                        else:
                            item_net = round(item_amount * net_ratio, 2)
                            cumulative_net += item_net
                        ratio = item_amount / total_gross if total_gross else Decimal("0")
                        item_after = total_after * ratio
                        item_discount = total_discount * ratio
                        sale_details.append(ReceivableSaleItem(
                            date=sale.sale_date,
                            sale_no=sale.sale_no,
                            product_name="三文鱼",
                            batch_name=wf_batch_map.get(sale.batch_id),
                            slaughter_date=batch_extra.get("slaughter_date"),
                            processing_plant_code=batch_extra.get("processing_plant_code"),
                            spec=item.spec,
                            quantity=item.box_count,
                            weight_kg=item.weight_kg,
                            unit_price=item.unit_price,
                            gross_amount=item_amount,
                            after_sales_adjustment=round(item_after, 2),
                            discount=round(item_discount, 2),
                            net_amount=round(item_net, 2),
                        ))
                else:
                    sale_details.append(ReceivableSaleItem(
                        date=sale.sale_date,
                        sale_no=sale.sale_no,
                        product_name="三文鱼",
                        batch_name=wf_batch_map.get(sale.batch_id),
                        slaughter_date=batch_extra.get("slaughter_date"),
                        processing_plant_code=batch_extra.get("processing_plant_code"),
                        spec=sale.spec,
                        quantity=sale.box_count,
                        weight_kg=sale.weight_kg,
                        unit_price=sale.unit_price,
                        gross_amount=_to_decimal(sale.gross_amount),
                        after_sales_adjustment=_to_decimal(sale.after_sales_adjustment),
                        discount=_to_decimal(sale.discount),
                        net_amount=_to_decimal(sale.net_amount),
                    ))
        for sale in all_fp_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                sale_details.append(ReceivableSaleItem(
                    date=sale.sale_date,
                    sale_no=f"FP-{sale.id}",
                    product_name="成品",
                    spec="成品",
                    quantity=sale.quantity,
                    weight_kg=sale.total_weight_kg,
                    unit_price=sale.unit_price,
                    gross_amount=_to_decimal(sale.gross_amount),
                    after_sales_adjustment=_to_decimal(sale.after_sales_adjustment),
                    discount=_to_decimal(sale.discount),
                    net_amount=_to_decimal(sale.net_amount),
                ))
        for sale in all_fp_v2_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                fp_v2_products = sale.products or []
                if fp_v2_products:
                    total_gross = sum(_to_decimal(p.total_amount) for p in fp_v2_products)
                    sale_net = _to_decimal(sale.net_amount)
                    net_ratio = sale_net / total_gross if total_gross else Decimal("0")
                    total_after = _to_decimal(sale.after_sales_adjustment)
                    total_discount = _to_decimal(sale.discount)
                    cumulative_net = Decimal("0")
                    for i, p in enumerate(fp_v2_products):
                        p_amount = _to_decimal(p.total_amount)
                        if i == len(fp_v2_products) - 1:
                            p_net = sale_net - cumulative_net
                        else:
                            p_net = round(p_amount * net_ratio, 2)
                            cumulative_net += p_net
                        ratio = p_amount / total_gross if total_gross else Decimal("0")
                        p_after = total_after * ratio
                        p_discount = total_discount * ratio
                        sale_details.append(ReceivableSaleItem(
                            date=sale.sale_date,
                            sale_no=sale.sale_no,
                            product_name=p.product_name or sale.product_name or "成品",
                            batch_name=sale.batch_no,
                            slaughter_date=p.slaughter_date,
                            processing_plant_code=p.factory,
                            spec=p.product_spec,
                            quantity=p.box_count,
                            weight_kg=p.weight_kg,
                            unit_price=p.unit_price,
                            gross_amount=p_amount,
                            after_sales_adjustment=round(p_after, 2),
                            discount=round(p_discount, 2),
                            net_amount=round(p_net, 2),
                        ))
                else:
                    sale_details.append(ReceivableSaleItem(
                        date=sale.sale_date,
                        sale_no=sale.sale_no,
                        product_name=sale.product_name or "成品",
                        batch_name=sale.batch_no,
                        slaughter_date=sale.slaughter_date,
                        processing_plant_code=sale.factory,
                        spec=sale.product_name or "成品",
                        quantity=sale.quantity,
                        weight_kg=sale.weight,
                        unit_price=sale.unit_price,
                        gross_amount=_to_decimal(sale.total_amount),
                        after_sales_adjustment=_to_decimal(sale.after_sales_adjustment),
                        discount=_to_decimal(sale.discount),
                        net_amount=_to_decimal(sale.net_amount),
                    ))
        sale_details.sort(key=lambda x: x.date)

        # 折扣明细
        for sale in all_wf_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.discount and sale.discount > 0:
                    discount_details.append(ReceivableDiscountItem(
                        date=sale.sale_date,
                        sale_no=sale.sale_no,
                        discount_amount=_to_decimal(sale.discount),
                        reason=None,
                    ))
                if sale.balance_adjustment:
                    discount_details.append(ReceivableDiscountItem(
                        date=sale.sale_date,
                        sale_no=sale.sale_no,
                        discount_amount=_to_decimal(sale.balance_adjustment),
                        reason=sale.balance_adjustment_reason or "账平调整",
                    ))
        for sale in all_fp_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.discount and sale.discount > 0:
                    discount_details.append(ReceivableDiscountItem(
                        date=sale.sale_date,
                        sale_no=f"FP-{sale.id}",
                        discount_amount=_to_decimal(sale.discount),
                        reason=None,
                    ))
        for sale in all_fp_v2_sales:
            if (start is None or sale.sale_date >= start) and (end is None or sale.sale_date <= end):
                if sale.discount and sale.discount > 0:
                    discount_details.append(ReceivableDiscountItem(
                        date=sale.sale_date,
                        sale_no=sale.sale_no,
                        discount_amount=_to_decimal(sale.discount),
                        reason=None,
                    ))
                if sale.balance_adjustment:
                    discount_details.append(ReceivableDiscountItem(
                        date=sale.sale_date,
                        sale_no=sale.sale_no,
                        discount_amount=_to_decimal(sale.balance_adjustment),
                        reason=sale.balance_adjustment_reason or "账平调整",
                    ))
        discount_details.sort(key=lambda x: x.date)

        # 售后明细（从 ReturnOrder + ReturnItem 获取完整数据）
        for r in all_return_orders:
            if (start is None or r.return_date >= start) and (end is None or r.return_date <= end):
                # 获取关联销售单号
                sale_no = None
                if r.whole_fish_sale_id:
                    sale = next((s for s in all_wf_sales if s.id == r.whole_fish_sale_id), None)
                    if sale:
                        sale_no = sale.sale_no

                # 获取 ReturnItem 明细（取第一行）
                return_items_result = await db.execute(
                    select(ReturnItem).where(ReturnItem.return_order_id == r.id)
                )
                return_items = return_items_result.scalars().all()
                item = return_items[0] if return_items else None

                aftersales_details.append(ReceivableAftersalesItem(
                    date=r.return_date,
                    return_no=r.return_no,
                    sale_no=sale_no,
                    quantity=float(item.weight_kg) if item else None,
                    unit_price=_to_decimal(item.unit_price) if item else None,
                    amount=_to_decimal(r.refund_amount),
                    reason=item.remarks if item else r.problem_description,
                    refund_method=r.refund_method.value if r.refund_method else None,
                ))
        aftersales_details.sort(key=lambda x: x.date)

        # 收支明细（真实银行流水 + 客户预付款 + 售后退款）
        # 合并收款：按 transaction_id 分组，多条相同 transaction_id 的销售单收款合并为一条
        from collections import defaultdict

        # 整鱼收款
        wf_receipt_groups = defaultdict(list)
        for receipt in all_wf_receipts:
            if (start is None or _txn_date(receipt) >= start) and (end is None or _txn_date(receipt) <= end):
                if receipt.payment_method != 'balance':  # 余额抵扣是内部调整，非银行流水
                    wf_receipt_groups[receipt.transaction_id].append(receipt)

        for txn_id, receipts in wf_receipt_groups.items():
            if txn_id is None or len(receipts) == 1:
                # 非合并收款，显示关联销售单号
                for receipt in receipts:
                    sale = next((s for s in all_wf_sales if s.id == receipt.sale_id), None)
                    receipt_details.append(ReceivableReceiptItem(
                        date=_txn_date(receipt),
                        amount=_to_decimal(receipt.amount),
                        payment_method=receipt.payment_method,
                        reference_no=sale.sale_no if sale else None,
                    ))
            else:
                # 合并收款：合并为一条记录，显示关联销售单
                # 使用 transaction.amount 作为权威值（合并收款时保存的实收金额）
                txn = receipts[0].transaction
                total_amount = _to_decimal(txn.amount) if txn else sum(_to_decimal(r.amount) for r in receipts)
                raw_total = sum(_to_decimal(r.amount) for r in receipts)

                # 检测数据异常：receipt 总和远大于权威值（如旧代码每个 receipt 都存了总额）
                is_data_corrupted = raw_total > total_amount * Decimal("1.5")

                # 正常数据：直接显示 receipt 金额
                if not is_data_corrupted:
                    related_sales = []
                    for r in receipts:
                        sale = next((s for s in all_wf_sales if s.id == r.sale_id), None)
                        related_sales.append({
                            "sale_no": sale.sale_no if sale else f"#{r.sale_id}",
                            "amount": float(_to_decimal(r.amount)),
                            "payable_amount": float(_to_decimal(sale.net_amount)) if sale else 0,
                        })
                else:
                    # 数据异常：按 FIFO（销售日期从早到晚）重新分配
                    # 先排序：销售日期早的在前面
                    sorted_pairs = sorted(
                        [(r, next((s for s in all_wf_sales if s.id == r.sale_id), None)) for r in receipts],
                        key=lambda x: (x[1].sale_date if x[1] else _txn_date(x[0]), x[1].id if x[1] else 0),
                    )
                    remaining = total_amount
                    related_sales = []
                    for r, sale in sorted_pairs:
                        payable = _to_decimal(sale.net_amount) if sale else Decimal("0")
                        if remaining <= 0:
                            display_amount = Decimal("0")
                        else:
                            display_amount = min(payable, remaining)
                            remaining -= display_amount
                        related_sales.append({
                            "sale_no": sale.sale_no if sale else f"#{r.sale_id}",
                            "amount": float(display_amount),
                            "payable_amount": float(payable),
                        })

                receipt_details.append(ReceivableReceiptItem(
                    date=_txn_date(receipts[0]),
                    amount=total_amount,
                    payment_method="batch_collect",
                    reference_no=f"合并收款：{len(receipts)} 个销售单",
                    is_batch_collect=True,
                    related_sales=related_sales,
                ))

        # 成品收款（旧版）
        fp_receipt_groups = defaultdict(list)
        for receipt in all_fp_receipts:
            if (start is None or _txn_date(receipt) >= start) and (end is None or _txn_date(receipt) <= end):
                if receipt.payment_method != 'balance':
                    fp_receipt_groups[receipt.transaction_id].append(receipt)

        for txn_id, receipts in fp_receipt_groups.items():
            if txn_id is None or len(receipts) == 1:
                # 非合并收款，显示关联销售单号
                for receipt in receipts:
                    sale = next((s for s in all_fp_sales if s.id == receipt.sale_id), None)
                    receipt_details.append(ReceivableReceiptItem(
                        date=_txn_date(receipt),
                        amount=_to_decimal(receipt.amount),
                        payment_method=receipt.payment_method,
                        reference_no=f"FP-{sale.id}" if sale else None,
                    ))
            else:
                # 合并收款：使用 transaction.amount 作为权威值
                txn = receipts[0].transaction
                total_amount = _to_decimal(txn.amount) if txn else sum(_to_decimal(r.amount) for r in receipts)
                raw_total = sum(_to_decimal(r.amount) for r in receipts)

                # 正常数据：直接显示 receipt 金额
                if not (raw_total > total_amount * Decimal("1.5")):
                    related_sales = []
                    for r in receipts:
                        sale = next((s for s in all_fp_sales if s.id == r.sale_id), None)
                        related_sales.append({
                            "sale_no": f"FP-{sale.id}" if sale else f"#{r.sale_id}",
                            "amount": float(_to_decimal(r.amount)),
                            "payable_amount": float(_to_decimal(sale.net_amount)) if sale else 0,
                        })
                else:
                    # 数据异常：按 FIFO（销售日期从早到晚）重新分配
                    sorted_pairs = sorted(
                        [(r, next((s for s in all_fp_sales if s.id == r.sale_id), None)) for r in receipts],
                        key=lambda x: (x[1].sale_date if x[1] else _txn_date(x[0]), x[1].id if x[1] else 0),
                    )
                    remaining = total_amount
                    related_sales = []
                    for r, sale in sorted_pairs:
                        payable = _to_decimal(sale.net_amount) if sale else Decimal("0")
                        if remaining <= 0:
                            display_amount = Decimal("0")
                        else:
                            display_amount = min(payable, remaining)
                            remaining -= display_amount
                        related_sales.append({
                            "sale_no": f"FP-{sale.id}" if sale else f"#{r.sale_id}",
                            "amount": float(display_amount),
                            "payable_amount": float(payable),
                        })

                receipt_details.append(ReceivableReceiptItem(
                    date=_txn_date(receipts[0]),
                    amount=total_amount,
                    payment_method="batch_collect",
                    reference_no=f"合并收款：{len(receipts)} 个销售单",
                    is_batch_collect=True,
                    related_sales=related_sales,
                ))

        # 以销定采 V2 收款
        fp_v2_receipt_groups = defaultdict(list)
        for receipt in all_fp_v2_receipts:
            if (start is None or _txn_date(receipt) >= start) and (end is None or _txn_date(receipt) <= end):
                if receipt.payment_method != 'balance':
                    fp_v2_receipt_groups[receipt.transaction_id].append(receipt)

        for txn_id, receipts in fp_v2_receipt_groups.items():
            if txn_id is None or len(receipts) == 1:
                # 非合并收款，显示关联销售单号
                for receipt in receipts:
                    sale = next((s for s in all_fp_v2_sales if s.id == receipt.sale_v2_id), None)
                    receipt_details.append(ReceivableReceiptItem(
                        date=_txn_date(receipt),
                        amount=_to_decimal(receipt.amount),
                        payment_method=receipt.payment_method,
                        reference_no=sale.sale_no if sale else None,
                    ))
            else:
                # 合并收款：使用 transaction.amount 作为权威值
                txn = receipts[0].transaction
                total_amount = _to_decimal(txn.amount) if txn else sum(_to_decimal(r.amount) for r in receipts)
                raw_total = sum(_to_decimal(r.amount) for r in receipts)

                # 正常数据：直接显示 receipt 金额
                if not (raw_total > total_amount * Decimal("1.5")):
                    related_sales = []
                    for r in receipts:
                        sale = next((s for s in all_fp_v2_sales if s.id == r.sale_v2_id), None)
                        related_sales.append({
                            "sale_no": sale.sale_no if sale else f"#{r.sale_v2_id}",
                            "amount": float(_to_decimal(r.amount)),
                            "payable_amount": float(_to_decimal(sale.net_amount)) if sale else 0,
                        })
                else:
                    # 数据异常：按 FIFO（销售日期从早到晚）重新分配
                    sorted_pairs = sorted(
                        [(r, next((s for s in all_fp_v2_sales if s.id == r.sale_v2_id), None)) for r in receipts],
                        key=lambda x: (x[1].sale_date if x[1] else _txn_date(x[0]), x[1].id if x[1] else 0),
                    )
                    remaining = total_amount
                    related_sales = []
                    for r, sale in sorted_pairs:
                        payable = _to_decimal(sale.net_amount) if sale else Decimal("0")
                        if remaining <= 0:
                            display_amount = Decimal("0")
                        else:
                            display_amount = min(payable, remaining)
                            remaining -= display_amount
                        related_sales.append({
                            "sale_no": sale.sale_no if sale else f"#{r.sale_v2_id}",
                            "amount": float(display_amount),
                            "payable_amount": float(payable),
                        })

                receipt_details.append(ReceivableReceiptItem(
                    date=_txn_date(receipts[0]),
                    amount=total_amount,
                    payment_method="batch_collect",
                    reference_no=f"合并收款：{len(receipts)} 个销售单",
                    is_batch_collect=True,
                    related_sales=related_sales,
                ))

        # 客户预付款（使用已提前查询的 prepayment_txs，按日期过滤，仅显示明细，汇总已在前面计算）
        for txn in prepayment_txs:
            if (start is None or txn.transaction_date >= start) and (end is None or txn.transaction_date <= end):
                # 先查该预付款 txn 实际分配给各销售单的金额（从 receipt 表）
                txn_receipts: dict[int, Decimal] = {}
                if txn.id and txn.related_sale_ids:
                    # 以销定采 V2
                    fp_receipt_result = await db.execute(
                        select(FinishedProductReceipt.sale_v2_id, func.sum(FinishedProductReceipt.amount))
                        .where(FinishedProductReceipt.transaction_id == txn.id)
                        .group_by(FinishedProductReceipt.sale_v2_id)
                    )
                    for sale_id, amount in fp_receipt_result.all():
                        txn_receipts[sale_id] = _to_decimal(amount)
                    # 进口整鱼
                    wf_receipt_result = await db.execute(
                        select(SalesReceipt.sale_id, func.sum(SalesReceipt.amount))
                        .where(SalesReceipt.transaction_id == txn.id)
                        .group_by(SalesReceipt.sale_id)
                    )
                    for sale_id, amount in wf_receipt_result.all():
                        txn_receipts[sale_id] = _to_decimal(amount)

                # 查询关联销售单详情（支持进口销售、以销定采、预包装销售三种类型）
                related_sale_nos = []
                related_sales = []
                if txn.related_sale_ids:
                    # 进口销售
                    wf_result = await db.execute(
                        select(WholeFishSale).where(WholeFishSale.id.in_(txn.related_sale_ids))
                    )
                    for sale in wf_result.scalars().all():
                        if sale.sale_no:
                            related_sale_nos.append(sale.sale_no)
                        receipt_amt = txn_receipts.get(sale.id, Decimal("0"))
                        # 如果没有 receipt 记录（旧数据），回退到显示剩余应付（冲减前）
                        if receipt_amt > 0:
                            display_amt = receipt_amt
                        else:
                            display_amt = max(Decimal("0"), _to_decimal(sale.net_amount) - _to_decimal(sale.paid_amount) + receipt_amt)
                        related_sales.append({
                            "sale_no": sale.sale_no or f"#{sale.id}",
                            "amount": float(display_amt),
                            "payable_amount": float(_to_decimal(sale.net_amount)),
                        })
                    # 以销定采 V2
                    fp_v2_result = await db.execute(
                        select(FinishedProductSaleV2).where(FinishedProductSaleV2.id.in_(txn.related_sale_ids))
                    )
                    for sale in fp_v2_result.scalars().all():
                        if sale.sale_no:
                            related_sale_nos.append(sale.sale_no)
                        receipt_amt = txn_receipts.get(sale.id, Decimal("0"))
                        if receipt_amt > 0:
                            display_amt = receipt_amt
                        else:
                            display_amt = max(Decimal("0"), _to_decimal(sale.net_amount) - _to_decimal(sale.paid_amount) + receipt_amt)
                        related_sales.append({
                            "sale_no": sale.sale_no or f"#{sale.id}",
                            "amount": float(display_amt),
                            "payable_amount": float(_to_decimal(sale.net_amount)),
                        })
                    # 预包装销售（旧版成品销售）
                    fp_result = await db.execute(
                        select(FinishedProductSale).where(FinishedProductSale.id.in_(txn.related_sale_ids))
                    )
                    for sale in fp_result.scalars().all():
                        related_sale_nos.append(f"FP-{sale.id}")
                        receipt_amt = txn_receipts.get(sale.id, Decimal("0"))
                        if receipt_amt > 0:
                            display_amt = receipt_amt
                        else:
                            display_amt = max(Decimal("0"), _to_decimal(sale.net_amount) - _to_decimal(sale.paid_amount) + receipt_amt)
                        related_sales.append({
                            "sale_no": f"FP-{sale.id}",
                            "amount": float(display_amt),
                            "payable_amount": float(_to_decimal(sale.net_amount)),
                        })
                
                reference_parts = []
                if txn.description:
                    reference_parts.append(txn.description)
                if txn.reference_no:
                    reference_parts.append(txn.reference_no)
                if related_sale_nos and not related_sales:
                    reference_parts.append(f"关联：{', '.join(related_sale_nos)}")
                
                receipt_details.append(ReceivableReceiptItem(
                    date=txn.transaction_date,
                    amount=_to_decimal(txn.amount),
                    payment_method="prepayment",
                    reference_no=f"客户预付款：{len(related_sales)} 个销售单" if related_sales else (" | ".join(reference_parts) if reference_parts else None),
                    related_sales=related_sales,
                ))

        # 售后退款（TransactionRecord 中的支出，金额为负）
        refund_conditions = [
            TransactionRecord.counterparty_id == customer.id,
            TransactionRecord.type == "expense",
            TransactionRecord.category == "sales_refund",
            TransactionRecord.is_confirmed.is_(True),
        ]
        if start is not None:
            refund_conditions.append(TransactionRecord.transaction_date >= start)
        if end is not None:
            refund_conditions.append(TransactionRecord.transaction_date <= end)

        refund_txn_result = await db.execute(
            select(TransactionRecord)
            .where(and_(*refund_conditions))
            .order_by(TransactionRecord.transaction_date)
        )
        for txn in refund_txn_result.scalars().all():
            receipt_details.append(ReceivableReceiptItem(
                date=txn.transaction_date,
                amount=-_to_decimal(txn.amount),  # 金额为负（支出）
                payment_method="sales_refund",
                reference_no=txn.description or txn.reference_no or None,
            ))

        receipt_details.sort(key=lambda x: x.date)

        # 只保留有数据的客户，或欠款不为0的客户
        if closing_balance != 0 or current_sales != 0 or current_receipts != 0 or current_aftersales != 0 or opening_balance != 0:
            items.append(ReceivableStatementItem(
                customer_id=customer.id,
                customer_name=customer.name,
                customer_code=customer.code,
                opening_balance=round(opening_balance, 2),
                current_sales=round(current_sales, 2),
                current_net_sales=round(current_net_sales, 2),
                current_receipts=round(current_receipts, 2),
                current_aftersales=round(current_aftersales, 2),
                current_discount=round(current_discount, 2),
                closing_balance=round(closing_balance, 2),
                details=details,
                sale_details=sale_details,
                discount_details=discount_details,
                aftersales_details=aftersales_details,
                receipt_details=receipt_details,
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


# ==================== CSV导出对账单 ====================

@router.get("/receivable-statements/export")
async def export_receivable_statements(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    customer_id: int | None = Query(None, description="按客户筛选，不传则导出全部"),
    db: AsyncSession = Depends(get_db),
):
    """
    导出应收对账单CSV（包含明细）
    """

    # 复用查询逻辑：先获取数据
    resp = await list_receivable_statements(
        skip=0,
        limit=500,
        start_date=start_date,
        end_date=end_date,
        customer_id=customer_id,
        db=db,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # BOM for Excel
    output.write("\ufeff")

    for item in resp.items:
        period_text = f"{start_date or '全部'} ~ {end_date or '全部'}"

        # 表头行
        writer.writerow([
            "客户名称", item.customer_name,
            "对账周期", period_text,
        ])
        writer.writerow([
            "期初欠款", str(item.opening_balance),
            "本期销售", str(item.current_sales),
            "本期收款", str(item.current_receipts),
            "本期售后", str(item.current_aftersales),
            "本期折扣", str(item.current_discount),
            "期末欠款", str(item.closing_balance),
        ])
        writer.writerow([])

        # 销售明细区域
        writer.writerow(["销售明细"])
        writer.writerow(["日期", "销售单号", "规格", "数量", "重量(kg)", "单价", "金额", "净额"])
        for d in item.sale_details:
            writer.writerow([
                str(d.date),
                d.sale_no,
                d.spec or "",
                d.quantity if d.quantity is not None else "",
                str(d.weight_kg) if d.weight_kg is not None else "",
                str(d.unit_price) if d.unit_price is not None else "",
                str(d.gross_amount),
                str(d.net_amount),
            ])
        writer.writerow([])

        # 折扣明细区域
        writer.writerow(["折扣明细"])
        writer.writerow(["日期", "销售单号", "折扣金额", "原因"])
        for d in item.discount_details:
            writer.writerow([
                str(d.date),
                d.sale_no,
                str(d.discount_amount),
                d.reason or "",
            ])
        writer.writerow([])

        # 售后明细区域
        writer.writerow(["售后明细"])
        writer.writerow(["日期", "销售单号", "退货单号", "重量", "单价", "金额", "原因", "退款方式"])
        for d in item.aftersales_details:
            writer.writerow([
                str(d.date),
                d.sale_no or "",
                d.return_no or "",
                str(d.quantity) if d.quantity is not None else "",
                str(d.unit_price) if d.unit_price is not None else "",
                str(d.amount),
                d.reason or "",
                d.refund_method or "",
            ])
        writer.writerow([])

        # 收支明细区域
        writer.writerow(["收支明细"])
        writer.writerow(["日期", "金额", "类型", "备注"])
        for d in item.receipt_details:
            if d.is_batch_collect and d.related_sales:
                # 合并收款：显示为一条，备注包含关联销售单
                related_info = "; ".join(
                    f"{s['sale_no']}: 实收{s['amount']} / 应付{s['payable_amount']}"
                    for s in d.related_sales
                )
                writer.writerow([
                    str(d.date),
                    str(d.amount),
                    "合并收款",
                    f"{d.reference_no} | {related_info}",
                ])
            else:
                writer.writerow([
                    str(d.date),
                    str(d.amount),
                    d.payment_method or "",
                    d.reference_no or "",
                ])
        writer.writerow([])
        writer.writerow([])

    content = output.getvalue()
    output.close()

    filename = f"应收对账单_{start_date or '全部'}_{end_date or '全部'}.csv"
    from urllib.parse import quote
    encoded_filename = quote(filename)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


# ==================== 应付款对账单 ====================

@router.get("/payable-statements", response_model=PayableStatementResponse)
async def list_payable_statements(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=500),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    purchase_type: str | None = Query(None, description="筛选: import=进口采购, domestic=国内采购, all/不传=全部"),
    importer_id: int | None = Query(None, description="按进口商筛选（仅进口采购有效）"),
    supplier_id: int | None = Query(None, description="按供应商筛选"),
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

    # 获取所有有采购发票关联的公司 + 国内采购单关联的供应商
    from sqlalchemy import distinct
    supplier_ids: set[int] = set()

    # 进口采购供应商
    if purchase_type in (None, "all", "import"):
        invoice_query = (
            select(distinct(ImportInvoice.supplier_id))
            .where(ImportInvoice.supplier_id.isnot(None))
        )
        if importer_id:
            invoice_query = invoice_query.where(ImportInvoice.importer_id == importer_id)
        if supplier_id:
            invoice_query = invoice_query.where(ImportInvoice.supplier_id == supplier_id)
        invoice_company_result = await db.execute(invoice_query)
        supplier_ids.update([r[0] for r in invoice_company_result.all() if r[0]])

    # 国内采购供应商（PurchaseOrderV2 + MaterialPurchaseOrder）
    if purchase_type in (None, "all", "domestic"):
        if not importer_id:  # 国内采购不关联进口商
            domestic_po_query = (
                select(distinct(PurchaseOrderV2.supplier_id))
                .where(PurchaseOrderV2.supplier_id.isnot(None))
            )
            if supplier_id:
                domestic_po_query = domestic_po_query.where(PurchaseOrderV2.supplier_id == supplier_id)
            domestic_po_result = await db.execute(domestic_po_query)
            supplier_ids.update([r[0] for r in domestic_po_result.all() if r[0]])

            material_po_query = (
                select(distinct(MaterialPurchaseOrder.supplier_id))
                .where(MaterialPurchaseOrder.supplier_id.isnot(None))
            )
            if supplier_id:
                material_po_query = material_po_query.where(MaterialPurchaseOrder.supplier_id == supplier_id)
            material_po_result = await db.execute(material_po_query)
            supplier_ids.update([r[0] for r in material_po_result.all() if r[0]])

    if not supplier_ids:
        return PayableStatementResponse(
            total=0, items=[], skip=skip, limit=limit,
            start_date=start_date, end_date=end_date, total_payable=Decimal("0"),
            purchase_type=purchase_type or "all",
        )

    supplier_result = await db.execute(
        select(Company)
        .where(Company.id.in_(supplier_ids))
        .order_by(Company.name)
    )
    suppliers = supplier_result.scalars().all()

    items: list[PayableStatementItem] = []
    total_payable = Decimal("0")

    for supplier in suppliers:
        # 该供应商相关的发票（按 supplier_id 关联）
        all_invoices = []
        if purchase_type in (None, "all", "import"):
            invoice_query = (
                select(ImportInvoice)
                .where(ImportInvoice.supplier_id == supplier.id)
            )
            if importer_id:
                invoice_query = invoice_query.where(ImportInvoice.importer_id == importer_id)
            invoice_query = invoice_query.order_by(ImportInvoice.invoice_date)
            invoice_result = await db.execute(invoice_query)
            all_invoices = invoice_result.scalars().all()

        # 该供应商相关的国内采购单（PurchaseOrderV2 + MaterialPurchaseOrder）
        all_domestic_pos = []
        all_material_pos = []
        if purchase_type in (None, "all", "domestic") and not importer_id:
            domestic_po_result = await db.execute(
                select(PurchaseOrderV2)
                .where(PurchaseOrderV2.supplier_id == supplier.id)
                .order_by(PurchaseOrderV2.purchase_date)
            )
            all_domestic_pos = domestic_po_result.scalars().all()

            material_po_result = await db.execute(
                select(MaterialPurchaseOrder)
                .where(MaterialPurchaseOrder.supplier_id == supplier.id)
                .order_by(MaterialPurchaseOrder.order_date)
            )
            all_material_pos = material_po_result.scalars().all()

        if not all_invoices and not all_domestic_pos and not all_material_pos:
            continue

        # 该供应商相关的购汇记录（通过发票ID、related_invoice_ids 或 batch_id 关联）
        all_exchanges = []
        if all_invoices:
            invoice_ids_list = [inv.id for inv in all_invoices]
            
            # 获取这些发票的 batch_id（通过 batch_invoices 关联表）
            from app.models import BatchInvoice
            batch_inv_result = await db.execute(
                select(BatchInvoice.batch_id)
                .where(BatchInvoice.invoice_id.in_(invoice_ids_list))
                .distinct()
            )
            batch_ids = [r[0] for r in batch_inv_result.all() if r[0]]
            
            # 单张发票购汇
            exchange_result = await db.execute(
                select(ExchangeRecord)
                .where(ExchangeRecord.invoice_id.in_(invoice_ids_list))
                .order_by(ExchangeRecord.exchange_date)
            )
            single_exchanges = list(exchange_result.scalars().all())
            
            # 合并购汇（related_invoice_ids 不为空）
            batch_result = await db.execute(
                select(ExchangeRecord)
                .where(ExchangeRecord.related_invoice_ids.isnot(None))
                .order_by(ExchangeRecord.exchange_date)
            )
            batch_exchanges = list(batch_result.scalars().all())
            
            # 批次购汇（通过 batch_id 关联，处理旧数据）
            batch_exchange_result = await db.execute(
                select(ExchangeRecord)
                .where(ExchangeRecord.batch_id.in_(batch_ids) if batch_ids else ExchangeRecord.id == -1)
                .order_by(ExchangeRecord.exchange_date)
            )
            batch_id_exchanges = list(batch_exchange_result.scalars().all())
            
            # 合并，去重，排序
            seen_ids = set()
            all_exchanges = []
            for ex in single_exchanges + batch_exchanges + batch_id_exchanges:
                if ex.id not in seen_ids:
                    seen_ids.add(ex.id)
                    # 合并购汇：检查是否关联到当前供应商的发票
                    if ex.related_invoice_ids and not ex.invoice_id:
                        if any(iid in invoice_ids_list for iid in ex.related_invoice_ids):
                            all_exchanges.append(ex)
                    # 批次购汇：检查 batch_id 是否匹配（处理旧数据 invoice_id/relaated_invoice_ids 为 null 的情况）
                    elif ex.batch_id and ex.batch_id in batch_ids and not ex.invoice_id and not ex.related_invoice_ids:
                        all_exchanges.append(ex)
                    else:
                        all_exchanges.append(ex)
            all_exchanges.sort(key=lambda x: x.exchange_date)

        # 判断币种：USD 供应商用美元记账，其他用人民币
        is_usd = (supplier.currency or "CNY") == "USD" if all_invoices else False

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
        # 国内采购单也计入期初（CNY）
        opening_domestic = Decimal("0")
        for po in all_domestic_pos:
            if start is not None and po.purchase_date < start:
                opening_domestic += _to_decimal(po.total_amount)

        # 物料采购单也计入期初（CNY）
        for po in all_material_pos:
            if start is not None and po.order_date < start:
                opening_domestic += _to_decimal(po.actual_total)

        opening_balance = opening_invoices + opening_domestic - opening_payments

        # 分组明细（新版）
        purchase_details: list[PayablePurchaseItem] = []
        expense_details: list[PayableExpenseItem] = []
        payment_details: list[PayablePaymentItem] = []
        exchange_details: list[PayableExchangeItem] = []  # 购汇明细（进口采购用）

        # 本期采购
        current_purchase = Decimal("0")
        current_expenses = Decimal("0")
        # 预加载本期发票的产品和税费（避免N+1）
        period_inv_ids = [inv.id for inv in all_invoices if (start is None or inv.invoice_date >= start) and (end is None or inv.invoice_date <= end)]
        prods_map_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(period_inv_ids))
        )
        prods_map = {}
        for p in prods_map_result.scalars().all():
            prods_map.setdefault(p.invoice_id, []).append(p)

        _taxes_map = {}
        if not is_usd:
            _taxes_map = await _batch_get_taxes(db, period_inv_ids)

        # 预加载发票的购汇记录映射（避免N+1）
        # 同时支持：单张发票购汇 + 合并购汇 + 批次购汇（batch_id）
        invoice_exchange_map = {}
        if period_inv_ids:
            # 获取这些发票的 batch_id
            from app.models import BatchInvoice
            batch_inv_result = await db.execute(
                select(BatchInvoice.batch_id, BatchInvoice.invoice_id)
                .where(BatchInvoice.invoice_id.in_(period_inv_ids))
            )
            inv_batch_map = {}  # invoice_id -> batch_id
            batch_ids = set()
            for row in batch_inv_result.all():
                inv_batch_map[row.invoice_id] = row.batch_id
                batch_ids.add(row.batch_id)
            
            # 单张发票购汇
            ex_result = await db.execute(
                select(ExchangeRecord).where(ExchangeRecord.invoice_id.in_(period_inv_ids))
            )
            for ex in ex_result.scalars().all():
                invoice_exchange_map[ex.invoice_id] = ex
            
            # 合并购汇：查询 related_invoice_ids 包含当前发票ID的记录
            batch_ex_result = await db.execute(
                select(ExchangeRecord).where(ExchangeRecord.related_invoice_ids.isnot(None))
            )
            for ex in batch_ex_result.scalars().all():
                if ex.related_invoice_ids:
                    related_ids = ex.related_invoice_ids if isinstance(ex.related_invoice_ids, list) else []
                    for iid in related_ids:
                        if iid in period_inv_ids and iid not in invoice_exchange_map:
                            invoice_exchange_map[iid] = ex
            
            # 批次购汇：通过 batch_id 关联（处理旧数据 invoice_id/related_invoice_ids 为 null 的情况）
            if batch_ids:
                batch_ex_result2 = await db.execute(
                    select(ExchangeRecord).where(ExchangeRecord.batch_id.in_(list(batch_ids)))
                )
                for ex in batch_ex_result2.scalars().all():
                    # 将该批次下的所有发票映射到这条购汇记录
                    for iid, bid in inv_batch_map.items():
                        if bid == ex.batch_id and iid not in invoice_exchange_map:
                            invoice_exchange_map[iid] = ex

        # 预加载进口商名称映射（避免N+1）
        importer_map = {}
        if period_inv_ids and all_invoices:
            importer_ids = list(set(inv.importer_id for inv in all_invoices if inv.importer_id))
            if importer_ids:
                importer_result = await db.execute(
                    select(Company.id, Company.name).where(Company.id.in_(list(importer_ids)))
                )
                importer_map = {row[0]: row[1] for row in importer_result.all()}

        for inv in all_invoices:
            if (start is None or inv.invoice_date >= start) and (end is None or inv.invoice_date <= end):
                prods = prods_map.get(inv.id, [])
                amount_usd = sum(_to_decimal(p.total_amount) for p in prods)
                if amount_usd == 0:
                    amount_usd = _to_decimal(inv.total_amount_usd)

                ex = await _get_invoice_exchange(db, inv.id, None)
                rate = _to_decimal(ex.exchange_rate) if ex else Decimal("7.0")
                if rate == 0:
                    rate = Decimal("7.0")
                purchase_cny = amount_usd * rate
                # USD 供应商按美元记账，CNY 供应商按人民币记账
                if is_usd:
                    current_purchase += amount_usd
                else:
                    current_purchase += purchase_cny

                # 获取该发票的实际购汇记录（单张或合并购汇）
                inv_ex = invoice_exchange_map.get(inv.id)
                # 判断购汇状态：有购汇记录则"已购汇"，否则"未购汇"
                exchange_status = "exchanged" if inv_ex else "not_exchanged"

                # 采购明细（增加购汇关联信息 + 进口商）
                purchase_details.append(PayablePurchaseItem(
                    date=inv.invoice_date,
                    invoice_no=inv.invoice_no or f"FP-{inv.id}",
                    amount_usd=round(amount_usd, 2),
                    exchange_rate=round(rate, 4),
                    amount_cny=round(purchase_cny, 2),
                    importer_name=importer_map.get(inv.importer_id) if inv.importer_id else None,
                    exchange_status=exchange_status,
                    exchange_no=inv_ex.exchange_no if inv_ex else None,
                    exchange_date=inv_ex.exchange_date if inv_ex else None,
                    exchange_rate_actual=round(_to_decimal(inv_ex.exchange_rate), 6) if inv_ex else None,
                    amount_usd_exchanged=round(_to_decimal(inv_ex.amount_usd), 2) if inv_ex else None,
                ))

                # 税费（进口采购不需要费用明细，跳过）
                # 税费仅在报关行汇总中显示

        # 国内采购单计入本期采购（CNY）
        for po in all_domestic_pos:
            if start is not None and end is not None and start <= po.purchase_date <= end or start is None and end is None:
                current_purchase += _to_decimal(po.total_amount)
                purchase_details.append(PayablePurchaseItem(
                    date=po.purchase_date,
                    invoice_no=po.purchase_no or f"CG-{po.id}",
                    amount_usd=Decimal("0"),
                    exchange_rate=None,
                    amount_cny=round(_to_decimal(po.total_amount), 2),
                ))

        # 物料采购单计入本期采购（CNY）
        for po in all_material_pos:
            if start is not None and end is not None and start <= po.order_date <= end or start is None and end is None:
                current_purchase += _to_decimal(po.actual_total)
                purchase_details.append(PayablePurchaseItem(
                    date=po.order_date,
                    invoice_no=po.order_no or f"WL-{po.id}",
                    amount_usd=Decimal("0"),
                    exchange_rate=None,
                    amount_cny=round(_to_decimal(po.actual_total), 2),
                ))

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

        # 购汇明细（进口采购用）
        for ex in all_exchanges:
            if start <= ex.exchange_date <= end:
                # 获取关联发票号列表
                invoice_nos = ""
                if ex.invoice_id:
                    inv = await db.get(ImportInvoice, ex.invoice_id)
                    if inv:
                        invoice_nos = inv.invoice_no or ""
                elif ex.related_invoice_ids:
                    # 合并购汇，查询多张发票号
                    inv_result = await db.execute(
                        select(ImportInvoice.invoice_no)
                        .where(ImportInvoice.id.in_(ex.related_invoice_ids))
                    )
                    invoice_nos = ", ".join([r[0] for r in inv_result.all() if r[0]])
                elif ex.batch_id:
                    # 通过 batch_id 获取关联发票号（旧数据）
                    batch_inv_result = await db.execute(
                        select(ImportInvoice.invoice_no)
                        .join(BatchInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
                        .where(BatchInvoice.batch_id == ex.batch_id)
                    )
                    invoice_nos = ", ".join([r[0] for r in batch_inv_result.all() if r[0]])

                exchange_details.append(PayableExchangeItem(
                    exchange_no=ex.exchange_no,
                    exchange_date=ex.exchange_date,
                    exchange_rate=round(_to_decimal(ex.exchange_rate), 6),
                    amount_usd=round(_to_decimal(ex.amount_usd), 2),
                    fee_cny=round(_to_decimal(ex.fee_cny), 2),
                    amount_cny=round(_to_decimal(ex.amount_cny), 2),
                    total_cny=round(_to_decimal(ex.amount_cny) + _to_decimal(ex.fee_cny), 2),
                    invoice_nos=invoice_nos or None,
                ))

        # 兼容旧版付款明细
        for ex in all_exchanges:
            if start <= ex.exchange_date <= end:
                if is_usd:
                    payment_details.append(PayablePaymentItem(
                        date=ex.exchange_date,
                        payment_type="exchange",
                        amount=round(_to_decimal(ex.amount_usd), 2),
                        reference_no=ex.exchange_no or None,
                        description=f"购汇 {ex.amount_usd:,.2f} USD",
                    ))
                else:
                    payment_details.append(PayablePaymentItem(
                        date=ex.exchange_date,
                        payment_type="exchange",
                        amount=round(_to_decimal(ex.amount_cny) + _to_decimal(ex.fee_cny), 2),
                        reference_no=ex.exchange_no or None,
                        description="购汇付款",
                    ))

        # 期末欠款
        closing_balance = opening_balance + current_purchase + current_expenses - current_payments

        # 明细
        details: list[PayableSupplierItem] = []
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
            if (start is None or inv.invoice_date >= start) and (end is None or inv.invoice_date <= end):
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

        # 先按日期排序，再计算累计余额
        details.sort(key=lambda x: x.date)

        # 重新计算累计余额
        running_balance = Decimal("0")
        for d in details:
            if d.type == "opening":
                running_balance = d.debit - d.credit
            elif d.type in ["invoice"]:
                running_balance += d.debit
            elif d.type in ["exchange", "payment"]:
                running_balance -= d.credit
            d.balance = running_balance

        # 期初条目固定在开头（如果有）
        opening_items = [d for d in details if d.type == "opening"]
        other_items = [d for d in details if d.type != "opening"]
        details = opening_items + other_items

        # 计算进口采购 USD 汇总
        # 进口总金额 = 所有采购发票金额
        total_import_usd = sum(d.amount_usd for d in purchase_details)
        # 已购汇金额 = 已购汇的发票金额（按发票金额统计，而非购汇登记金额）
        total_exchanged_usd = sum(d.amount_usd for d in purchase_details if d.exchange_status == "exchanged")
        total_unexchanged_usd = total_import_usd - total_exchanged_usd
        # 购汇合计 CNY 仍按实际购汇记录统计（含手续费）
        total_exchanged_cny = sum(d.total_cny for d in exchange_details)

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
                total_import_usd=round(total_import_usd, 2),
                total_exchanged_usd=round(total_exchanged_usd, 2),
                total_unexchanged_usd=round(total_unexchanged_usd, 2),
                total_exchanged_cny=round(total_exchanged_cny, 2),
                details=details,
                purchase_details=purchase_details,
                expense_details=expense_details,
                payment_details=payment_details,
                exchange_details=exchange_details,
            ))
            total_payable += closing_balance

    # 单独汇总报关行应付款（按报关行分组）
    if purchase_type in (None, "all", "import"):
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

            broker_details: list[PayableSupplierItem] = []
            broker_expense_details: list[PayableExpenseItem] = []
            broker_payment_details: list[PayablePaymentItem] = []

            # 获取清关费用明细
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
                # 费用明细（含报关行费用细项）
                broker_expense_details.append(PayableExpenseItem(
                    date=cc.cost_date,
                    invoice_no=inv_no,
                    expense_type="clearance_fee",
                    description="清关费用",
                    amount=round(_to_decimal(cc.total_cost), 2),
                    gross_weight_kg=cc.gross_weight_kg,
                    freight_fee=_to_decimal(cc.freight_fee) if cc.freight_fee else None,
                    inspection_fee=_to_decimal(cc.inspection_fee) if cc.inspection_fee else None,
                    quarantine_fee=_to_decimal(cc.quarantine_fee) if cc.quarantine_fee else None,
                    other_costs=_to_decimal(cc.other_costs) if cc.other_costs else None,
                    clearance_fee=_to_decimal(cc.clearance_fee) if cc.clearance_fee else None,
                    total_cost=_to_decimal(cc.total_cost) if cc.total_cost else None,
                ))

            # 获取交易流水中的清关费支付（付款给该报关行）
            broker_payments = Decimal("0")
            transaction_result = await db.execute(
                select(TransactionRecord)
                .where(TransactionRecord.category == "clearance_payment")
                .where(TransactionRecord.counterparty_id == broker_id)
                .where(TransactionRecord.transaction_date >= start)
                .where(TransactionRecord.transaction_date <= end)
                .where(TransactionRecord.type == "expense")
                .order_by(TransactionRecord.transaction_date)
            )
            tx_records = transaction_result.scalars().all()
            for tx in tx_records:
                payment_amount = _to_decimal(tx.amount)
                broker_payments += payment_amount
                broker_details.append(PayableSupplierItem(
                    date=tx.transaction_date,
                    type="payment",
                    description=f"付款 ({tx.reference_no or '无单号'})",
                    debit=Decimal("0"),
                    credit=payment_amount,
                    balance=Decimal("0"),
                ))
                # 付款明细
                broker_payment_details.append(PayablePaymentItem(
                    date=tx.transaction_date,
                    payment_type="clearance_payment",
                    amount=round(payment_amount, 2),
                    reference_no=tx.reference_no or None,
                    description=tx.description or None,
                ))

            # 先按日期排序，再计算累计余额
            broker_details.sort(key=lambda x: x.date)

            # 重新计算累计余额（费用 - 付款）
            running_balance = Decimal("0")
            for d in broker_details:
                if d.type == "invoice":
                    running_balance += d.debit
                elif d.type == "payment":
                    running_balance -= d.credit
                d.balance = running_balance

            items.append(PayableStatementItem(
                supplier_id=broker_id,
                supplier_name=broker_name,
                supplier_type="customs_broker",
                supplier_code=None,
                opening_balance=Decimal("0"),
                current_purchase=Decimal("0"),
                current_expenses=round(broker_total, 2),
                current_payments=round(broker_payments, 2),
                closing_balance=round(broker_total - broker_payments, 2),
                details=broker_details,
                purchase_details=[],
                expense_details=broker_expense_details,
                payment_details=broker_payment_details,
            ))
            total_payable += broker_total - broker_payments

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
        purchase_type=purchase_type or "all",
    )


# ==================== 应付对账单CSV导出 ====================

@router.get("/payable-statements/export")
async def export_payable_statements(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    supplier_id: int | None = Query(None, description="按供应商筛选，不传则导出全部"),
    purchase_type: str | None = Query(None, description="筛选: import=进口采购, domestic=国内采购, all/不传=全部"),
    db: AsyncSession = Depends(get_db),
):
    """
    导出应付对账单CSV（包含明细）
    """

    # 复用查询逻辑
    resp = await list_payable_statements(
        skip=0,
        limit=500,
        start_date=start_date,
        end_date=end_date,
        purchase_type=purchase_type,
        db=db,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # BOM for Excel
    output.write("\ufeff")

    for item in resp.items:
        # 过滤指定供应商
        if supplier_id and item.supplier_id != supplier_id:
            continue

        period_text = f"{start_date or '全部'} ~ {end_date or '全部'}"

        # 表头行
        writer.writerow([
            "供应商名称", item.supplier_name,
            "对账周期", period_text,
        ])
        writer.writerow([
            "期初欠款", str(item.opening_balance),
            "本期采购", str(item.current_purchase),
            "本期费用", str(item.current_expenses),
            "本期付款", str(item.current_payments),
            "期末欠款", str(item.closing_balance),
        ])
        writer.writerow([])

        # 采购明细
        if item.purchase_details:
            writer.writerow(["采购明细"])
            writer.writerow(["日期", "发票号", "金额(USD)", "汇率", "金额(CNY)"])
            for d in item.purchase_details:
                writer.writerow([
                    str(d.date),
                    d.invoice_no or "",
                    str(d.amount_usd),
                    str(d.exchange_rate or ""),
                    str(d.amount_cny),
                ])
            writer.writerow([])

        # 费用明细
        if item.expense_details:
            writer.writerow(["费用明细"])
            writer.writerow(["日期", "发票号", "费用类型", "说明", "金额"])
            for d in item.expense_details:
                writer.writerow([
                    str(d.date),
                    d.invoice_no or "",
                    d.expense_type or "",
                    d.description or "",
                    str(d.amount),
                ])
            writer.writerow([])

        # 付款明细
        if item.payment_details:
            writer.writerow(["付款明细"])
            writer.writerow(["日期", "付款类型", "付款金额", "备注"])
            for d in item.payment_details:
                writer.writerow([
                    str(d.date),
                    d.payment_type or "",
                    str(d.amount),
                    d.description or d.reference_no or "",
                ])
            writer.writerow([])

        writer.writerow([])
        writer.writerow([])

    content = output.getvalue()
    output.close()

    filename = f"应付对账单_{start_date or '全部'}_{end_date or '全部'}.csv"
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ==================== 应付月份对账单 ====================

@router.get("/payable-statements/monthly", response_model=PayableMonthlyResponse)
async def get_payable_monthly(
    supplier_id: int = Query(..., description="供应商ID"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    供应商月份对账单 - 按月汇总应付明细

    例：威揽 2026年1-5月对账单
    """
    from datetime import datetime as _dt
    today = _dt.now().date()
    if not start_date:
        start_date = today.replace(day=1).isoformat()
    if not end_date:
        end_date = today.isoformat()

    # 获取供应商
    supplier = await db.get(Company, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="供应商不存在")

    # 判断币种
    is_usd = (supplier.currency or "CNY") == "USD"
    currency = "USD" if is_usd else "CNY"

    # 获取所有发票
    invoice_result = await db.execute(
        select(ImportInvoice)
        .where(ImportInvoice.supplier_id == supplier_id)
        .order_by(ImportInvoice.invoice_date)
    )
    all_invoices = invoice_result.scalars().all()

    # 获取所有购汇
    invoice_ids = [inv.id for inv in all_invoices]
    exchange_result = await db.execute(
        select(ExchangeRecord)
        .where(ExchangeRecord.invoice_id.in_(invoice_ids))
        .order_by(ExchangeRecord.exchange_date)
    )
    all_exchanges = exchange_result.scalars().all()

    # 按月分组
    from collections import defaultdict
    month_invoices = defaultdict(list)
    month_exchanges = defaultdict(list)

    for inv in all_invoices:
        m = inv.invoice_date.strftime("%Y-%m")
        month_invoices[m].append(inv)

    for ex in all_exchanges:
        if ex.exchange_date:
            m = ex.exchange_date.strftime("%Y-%m")
            month_exchanges[m].append(ex)

    # 所有月份（排序）
    all_months = sorted(set(list(month_invoices.keys()) + list(month_exchanges.keys())))
    if not all_months:
        return PayableMonthlyResponse(
            supplier_id=supplier_id,
            supplier_name=supplier.name,
            supplier_code=supplier.code,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
            total_payable=Decimal("0"),
            months=[],
        )

    months_data: list[PayableMonthlyItem] = []
    running_balance = Decimal("0")

    for month in all_months:
        # 期初 = 上一个月的期末
        opening = running_balance

        current_purchase = Decimal("0")
        current_expenses = Decimal("0")
        current_payments = Decimal("0")
        details: list[PayableSupplierItem] = []

        # 本月发票
        for inv in month_invoices.get(month, []):
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

            current_purchase += debit
            details.append(PayableSupplierItem(
                date=inv.invoice_date,
                type="invoice",
                invoice_no=inv.invoice_no,
                description=desc,
                debit=round(debit, 2),
                credit=Decimal("0"),
                balance=Decimal("0"),
            ))

            # 税费
            tax = await _get_invoice_taxes(db, inv.id)
            if tax and not is_usd:
                tax_total = _to_decimal(tax.import_duty) + _to_decimal(tax.import_vat)
                if tax_total > 0:
                    current_expenses += tax_total
                    details.append(PayableSupplierItem(
                        date=inv.invoice_date,
                        type="invoice",
                        description="进口税费",
                        debit=round(tax_total, 2),
                        credit=Decimal("0"),
                        balance=Decimal("0"),
                    ))

        # 本月付款
        for ex in month_exchanges.get(month, []):
            if is_usd:
                credit = _to_decimal(ex.amount_usd)
                desc = f"购汇付款 ({ex.amount_usd:,.2f} USD)"
            else:
                credit = _to_decimal(ex.amount_cny) + _to_decimal(ex.fee_cny)
                desc = "购汇付款"

            current_payments += credit
            details.append(PayableSupplierItem(
                date=ex.exchange_date,
                type="exchange",
                description=desc,
                debit=Decimal("0"),
                credit=round(credit, 2),
                balance=Decimal("0"),
            ))

        # 计算本月期末
        closing = opening + current_purchase + current_expenses - current_payments

        # 重新计算累计余额
        bal = opening
        for d in details:
            if d.type == "invoice":
                bal += d.debit
            elif d.type == "exchange":
                bal -= d.credit
            d.balance = round(bal, 2)

        running_balance = closing

        # 月份标签
        y, m = month.split("-")
        month_label = f"{y}年{int(m)}月"

        months_data.append(PayableMonthlyItem(
            month=month,
            month_label=month_label,
            opening_balance=round(opening, 2),
            current_purchase=round(current_purchase, 2),
            current_expenses=round(current_expenses, 2),
            current_payments=round(current_payments, 2),
            closing_balance=round(closing, 2),
            details=details,
        ))

    total_payable = months_data[-1].closing_balance if months_data else Decimal("0")

    return PayableMonthlyResponse(
        supplier_id=supplier_id,
        supplier_name=supplier.name,
        supplier_code=supplier.code,
        currency=currency,
        start_date=start_date,
        end_date=end_date,
        total_payable=total_payable,
        months=months_data,
    )


# ==================== 三大财务报表 ====================

@router.get("/financial-statements", response_model=FinancialStatements)
async def get_financial_statements(
    period_type: str = Query("current_quarter"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    retail_revenue: Decimal = Query(Decimal("0")),
    retail_cost: Decimal = Query(Decimal("0")),
    db: AsyncSession = Depends(get_db),
):
    """
    三大财务报表：利润表、资产负债表、现金流量表

    参考 salmon-finance-v4 shareholder_report.py 实现
    """
    from datetime import datetime as _dt
    from datetime import timedelta

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

    # ========== 1. 获取周期内已购汇批次（利润表用）==========
    # 只有周期内至少有一张发票的已购汇批次才计入利润表
    batch_date_result = await db.execute(
        select(Batch.id)
        .join(BatchInvoice, BatchInvoice.batch_id == Batch.id)
        .join(ImportInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
        .where(
            ImportInvoice.exchange_status == ExchangeStatus.COMPLETED,
            ImportInvoice.invoice_date >= sdt,
            ImportInvoice.invoice_date <= edt,
        )
        .distinct()
    )
    purchased_batch_ids = [r[0] for r in batch_date_result.all() if r[0]]

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
        sale_ids = []
        for sale in sales_list:
            total_sales_net += _to_decimal(sale.net_amount)
            total_sales_gross += _to_decimal(sale.gross_amount)
            total_scan_fee += _to_decimal(sale.scan_fee)
            total_rounding += _to_decimal(sale.rounding_adjustment)
            total_after_sales += _to_decimal(sale.after_sales_adjustment)
            total_discount += _to_decimal(sale.discount)
            sale_ids.append(sale.id)

        # 佣金从 CommissionRecord 统一查询（消除双轨制）
        if sale_ids:
            commission_result = await db.execute(
                select(func.sum(CommissionRecord.commission_amount))
                .where(CommissionRecord.sale_id.in_(sale_ids))
            )
            total_commission += _to_decimal(commission_result.scalar())

        # 购汇（支持多行汇总）--按周期过滤
        ex_result = await db.execute(
            select(ExchangeRecord)
            .where(
                ExchangeRecord.batch_id == batch_id,
                ExchangeRecord.exchange_date >= sdt,
                ExchangeRecord.exchange_date <= edt,
            )
            .order_by(ExchangeRecord.created_at.desc())
        )
        exchange_records = ex_result.scalars().all()
        for ex in exchange_records:
            total_exchange_payment += _to_decimal(ex.amount_cny)
            total_exchange_fee += _to_decimal(ex.fee_cny)

        # 批次发票
        bi_result = await db.execute(
            select(BatchInvoice).where(BatchInvoice.batch_id == batch_id)
        )
        bi_rows = bi_result.scalars().all()
        invoice_ids = [bi.invoice_id for bi in bi_rows]

        # 批量获取发票日期信息 + 预加载税费/清关（避免N+1）
        inv_result = await db.execute(
            select(ImportInvoice.id, ImportInvoice.invoice_date)
            .where(ImportInvoice.id.in_(invoice_ids))
        )
        inv_dates = {row[0]: row[1] for row in inv_result.all()}

        taxes_map = await _batch_get_taxes(db, invoice_ids)
        clearances_map = await _batch_get_clearances(db, invoice_ids)

        # 税费和清关（按发票日期过滤，从预加载字典获取）
        for inv_id in invoice_ids:
            inv_date = inv_dates.get(inv_id)
            if inv_date and inv_date >= sdt and inv_date <= edt:
                tax = taxes_map.get(inv_id)
                if tax:
                    total_import_vat += _to_decimal(tax.import_vat)
                    total_import_duty += _to_decimal(tax.import_duty)

                clearance = clearances_map.get(inv_id)
                if clearance:
                    total_clearance += (
                        _to_decimal(clearance.clearance_fee) +
                        _to_decimal(clearance.freight_fee) +
                        _to_decimal(clearance.inspection_fee) +
                        _to_decimal(clearance.quarantine_fee) +
                        _to_decimal(clearance.other_costs)
                    )

        # 损耗（使用公共函数）
        shrinkage = await _calc_batch_shrinkage(db, batch_id, invoice_ids, sales_list)
        total_shrinkage += shrinkage

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

    # ========== 利润表计算（方案A：全透明口径，无隐藏扣减）==========
    # 1. 整鱼批发销售收入 = gross_amount（理论全额，不做任何隐含扣减）
    wholesale_gross = total_sales_gross

    # 2. 收入扣减项（明确列出，不偷偷扣）
    revenue_deductions = total_discount + total_after_sales + total_rounding + total_scan_fee

    # 3. 主营业务收入净额 = 理论全额 - 明确扣减项
    wholesale_net = wholesale_gross - revenue_deductions

    # 4. 总营业收入 = 主营业务净额 + 零售收入
    total_revenue = wholesale_net + retail_revenue

    # 5. 营业成本（COGS）
    cogs = total_exchange_payment + total_exchange_fee + total_import_vat + total_import_duty + total_clearance + round(total_shrinkage, 2)

    # 6. 销售费用（仅含真正的销售费用，不含已在收入中扣减的项目）
    sales_expenses = total_commission + total_other + retail_cost

    # 7. 营业利润 / 净利润
    operating_profit = total_revenue - cogs - sales_expenses - total_daily_expense
    net_profit = operating_profit

    # 日常支出明细项
    daily_expense_items = []
    for cat, amount in sorted(daily_expense_by_category.items(), key=lambda x: -x[1]):
        if amount > 0:
            daily_expense_items.append(
                FinancialStatementItem(label=f"        {cat}", amount=round(amount, 2), indent=2, is_deduction=True)
            )

    # ========== 构建利润表（透明结构）==========
    income_items = [
        # ── 一、营业收入 ──
        FinancialStatementItem(label="一、营业收入", amount=round(total_revenue, 2), is_header=True),
        FinancialStatementItem(label="    1. 整鱼批发销售收入（理论全额）", amount=round(wholesale_gross, 2), indent=1),
        FinancialStatementItem(label="        减：折扣", amount=round(total_discount, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        减：售后调整", amount=round(total_after_sales, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        减：抹零", amount=round(total_rounding, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        减：扫码手续费", amount=round(total_scan_fee, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="    2. 主营业务收入净额", amount=round(wholesale_net, 2), indent=1, is_subtotal=True),
        FinancialStatementItem(label="    3. 零售销售收入", amount=round(retail_revenue, 2), indent=1, note="手动输入" if retail_revenue > 0 else "待开发"),
        FinancialStatementItem(label="    营业收入合计", amount=round(total_revenue, 2), indent=1, is_subtotal=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),

        # ── 二、营业成本 ──
        FinancialStatementItem(label="二、营业成本", amount=round(cogs, 2), is_header=True, is_deduction=True),
        FinancialStatementItem(label="    减：进口成本", amount=round(cogs, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="        采购成本（购汇付款）", amount=round(total_exchange_payment, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        购汇手续费", amount=round(total_exchange_fee, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        进口增值税", amount=round(total_import_vat, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        进口关税", amount=round(total_import_duty, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        清关费及运费", amount=round(total_clearance, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="        账面损耗", amount=round(total_shrinkage, 2), indent=2, is_deduction=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),

        # ── 三、销售费用 ──
        FinancialStatementItem(label="三、销售费用", amount=round(sales_expenses, 2), is_header=True, is_deduction=True),
        FinancialStatementItem(label="    业务员提成", amount=round(total_commission, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="    其他支出（批次）", amount=round(total_other, 2), indent=1, is_deduction=True),
        FinancialStatementItem(label="    零售销售成本", amount=round(retail_cost, 2), indent=1, is_deduction=True, note="手动输入" if retail_cost > 0 else "待开发"),
        FinancialStatementItem(label="", amount=None, is_spacer=True),

        # ── 四、日常经营支出 ──
        FinancialStatementItem(label="四、日常经营支出", amount=round(total_daily_expense, 2), is_header=True, is_deduction=True),
        FinancialStatementItem(label="    减：日常经营支出", amount=round(total_daily_expense, 2), indent=1, is_deduction=True, note=f"共{len(daily_expense_by_category)}项"),
        *daily_expense_items,
        FinancialStatementItem(label="", amount=None, is_spacer=True),

        # ── 利润 ──
        FinancialStatementItem(label="营业利润", amount=round(operating_profit, 2), is_header=True, is_highlight=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="净利润", amount=round(net_profit, 2), is_header=True, is_total=True),
    ]

    income_statement = IncomeStatement(
        title="利润表",
        subtitle="（未经审计）",
        items=income_items,
        summary={
            "wholesale_gross": round(wholesale_gross, 2),
            "revenue_deductions": round(revenue_deductions, 2),
            "wholesale_net": round(wholesale_net, 2),
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
    # 货币资金 = 所有银行账户 current_balance 之和（实时余额，最准确）
    bank_result = await db.execute(select(BankAccount))
    banks = bank_result.scalars().all()
    cash_balance = round(sum(_to_decimal(b.current_balance) for b in banks), 2)
    opening_balance = round(sum(_to_decimal(b.opening_balance) for b in banks), 2)

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

    # 存货 = 未报关发票金额 × 预估汇率（优先）或 7.0
    uncleared_result = await db.execute(
        select(ImportInvoice).where(
            ImportInvoice.customs_status != "cleared",
            ImportInvoice.invoice_date <= edt,
        )
    )
    uncleared_invoices = uncleared_result.scalars().all()
    total_uncleared_usd = Decimal("0")
    inventory_value = Decimal("0")
    for inv in uncleared_invoices:
        prod_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
        )
        prods = prod_result.scalars().all()
        amount = sum(_to_decimal(p.total_amount) for p in prods)
        if amount == 0:
            amount = _to_decimal(inv.total_amount_usd)
        total_uncleared_usd += amount
        rate = _to_decimal(inv.estimated_exchange_rate) if inv.estimated_exchange_rate else Decimal("7.0")
        if rate == 0:
            rate = Decimal("7.0")
        inventory_value += amount * rate
    inventory_value = round(inventory_value, 2)

    # 应付账款 = 已清关但未购汇的发票金额 × 预估汇率（优先）或 7.0
    unpaid_invoice_result = await db.execute(
        select(ImportInvoice).where(
            ImportInvoice.exchange_status != "completed",
            ImportInvoice.invoice_date <= edt,
        )
    )
    unpaid_invoices = unpaid_invoice_result.scalars().all()
    total_owed_usd = Decimal("0")
    accounts_payable = Decimal("0")
    for inv in unpaid_invoices:
        prod_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
        )
        prods = prod_result.scalars().all()
        amount = sum(_to_decimal(p.total_amount) for p in prods)
        if amount == 0:
            amount = _to_decimal(inv.total_amount_usd)
        total_owed_usd += amount
        rate = _to_decimal(inv.estimated_exchange_rate) if inv.estimated_exchange_rate else Decimal("7.0")
        if rate == 0:
            rate = Decimal("7.0")
        accounts_payable += amount * rate
    accounts_payable = round(accounts_payable, 2)

    # 累计利润（截止到 end_date 的全部已购汇批次）
    all_purchased_batch_result = await db.execute(
        select(Batch.id)
        .join(BatchInvoice, BatchInvoice.batch_id == Batch.id)
        .join(ImportInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
        .where(
            ImportInvoice.exchange_status == ExchangeStatus.COMPLETED,
            ImportInvoice.invoice_date <= edt,
        )
        .distinct()
    )
    all_purchased_batch_ids = [r[0] for r in all_purchased_batch_result.all() if r[0]]

    cumulative_profit = Decimal("0")
    for batch_id in all_purchased_batch_ids:
        sales_result = await db.execute(
            select(WholeFishSale).where(WholeFishSale.batch_id == batch_id)
        )
        sales_list = sales_result.scalars().all()
        sales_net = sum(_to_decimal(s.net_amount) for s in sales_list)

        ex_result = await db.execute(
            select(ExchangeRecord).where(ExchangeRecord.batch_id == batch_id)
        )
        exchange_records = ex_result.scalars().all()
        ex_payment = Decimal("0")
        ex_fee = Decimal("0")
        for ex in exchange_records:
            ex_payment += _to_decimal(ex.amount_cny)
            ex_fee += _to_decimal(ex.fee_cny)

        bi_result = await db.execute(
            select(BatchInvoice).where(BatchInvoice.batch_id == batch_id)
        )
        invoice_ids = [bi.invoice_id for bi in bi_result.scalars().all()]

        # 批量预加载税费和清关（避免N+1）
        taxes_map = await _batch_get_taxes(db, invoice_ids)
        clearances_map = await _batch_get_clearances(db, invoice_ids)

        taxes = Decimal("0")
        clearance_cost = Decimal("0")
        for inv_id in invoice_ids:
            tax = taxes_map.get(inv_id)
            if tax:
                taxes += _to_decimal(tax.import_vat) + _to_decimal(tax.import_duty)
            clearance = clearances_map.get(inv_id)
            if clearance:
                clearance_cost += (
                    _to_decimal(clearance.clearance_fee) +
                    _to_decimal(clearance.freight_fee) +
                    _to_decimal(clearance.inspection_fee) +
                    _to_decimal(clearance.quarantine_fee) +
                    _to_decimal(clearance.other_costs)
                )

        total_exp = ex_payment + ex_fee + taxes + clearance_cost
        # 损耗（使用公共函数）
        shrink = await _calc_batch_shrinkage(db, batch_id, invoice_ids, sales_list)

        cumulative_profit += sales_net - total_exp - shrink

    total_assets = cash_balance + accounts_receivable + inventory_value
    total_liabilities = accounts_payable
    owners_equity = round(cumulative_profit, 2)
    balance_check = round(total_assets - total_liabilities - owners_equity, 2)

    balance_items = [
        FinancialStatementItem(label="资产", amount=None, is_section=True),
        FinancialStatementItem(label="流动资产：", amount=None, is_header=True),
        FinancialStatementItem(label="    货币资金", amount=cash_balance, indent=1, note=f"银行账户余额合计 · 期初 {opening_balance}"),
        FinancialStatementItem(label="    应收账款", amount=round(accounts_receivable, 2), indent=1),
        FinancialStatementItem(label="    存货", amount=inventory_value, indent=1, note=f"未报关 · 优先按预估汇率折算${total_uncleared_usd:,.2f}USD"),
        FinancialStatementItem(label="流动资产合计", amount=round(total_assets, 2), is_subtotal=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="资产总计", amount=round(total_assets, 2), is_total=True),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="负债", amount=None, is_section=True),
        FinancialStatementItem(label="    应付账款", amount=round(accounts_payable, 2), indent=1, note=f"未购汇 · 优先按预估汇率折算${total_owed_usd:,.2f}USD"),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="累计利润", amount=owners_equity, indent=0, note="已购汇批次实现的利润"),
        FinancialStatementItem(label="", amount=None, is_spacer=True),
        FinancialStatementItem(label="平衡校验", amount=round(total_assets - total_liabilities - owners_equity, 2), is_total=True, note="差额=未购汇总次待结算毛利+预估汇率偏差（批次结算制下不为0属正常）"),
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
    # 销售商品收到的现金 = 周期内实际收款（收付实现制，非权责发生制）
    period_receipt_result = await db.execute(
        select(func.coalesce(func.sum(SalesReceipt.amount), 0))
        .where(
            SalesReceipt.receipt_date >= sdt,
            SalesReceipt.receipt_date <= edt,
        )
    )
    cash_from_sales = round(_to_decimal(period_receipt_result.scalar()), 2)

    # 成品销售收款
    fp_period_receipt_result = await db.execute(
        select(func.coalesce(func.sum(FinishedProductReceipt.amount), 0))
        .where(
            FinishedProductReceipt.receipt_date >= sdt,
            FinishedProductReceipt.receipt_date <= edt,
        )
    )
    cash_from_sales += round(_to_decimal(fp_period_receipt_result.scalar()), 2)

    # 周期内日常收入
    cash_from_other_result = await db.execute(
        select(func.coalesce(func.sum(TransactionRecord.amount), 0))
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
            func.coalesce(func.sum(ExchangeRecord.amount_cny), 0).label("cash_for_purchase"),
            func.coalesce(func.sum(ExchangeRecord.fee_cny), 0).label("cash_for_exchange_fee"),
        )
        .where(
            ExchangeRecord.exchange_date >= sdt,
            ExchangeRecord.exchange_date <= edt,
        )
    )
    row = period_exchange_result.first()
    cash_for_purchase = _to_decimal(row[0] if row else 0)
    cash_for_exchange_fee = _to_decimal(row[1] if row else 0)

    # 周期内税费（独立查询，避免 INNER JOIN 丢数据）
    period_tax_result = await db.execute(
        select(func.coalesce(func.sum(ImportTax.import_vat + ImportTax.import_duty), 0))
        .join(ImportInvoice, ImportTax.invoice_id == ImportInvoice.id)
        .where(
            ImportInvoice.invoice_date >= sdt,
            ImportInvoice.invoice_date <= edt,
        )
    )
    cash_for_tax = _to_decimal(period_tax_result.scalar())

    # 周期内清关费（独立查询）
    period_clearance_result = await db.execute(
        select(func.coalesce(func.sum(
            ClearanceCost.clearance_fee + ClearanceCost.freight_fee +
            ClearanceCost.inspection_fee + ClearanceCost.quarantine_fee +
            ClearanceCost.other_costs
        ), 0))
        .join(ImportInvoice, ClearanceCost.invoice_id == ImportInvoice.id)
        .where(
            ImportInvoice.invoice_date >= sdt,
            ImportInvoice.invoice_date <= edt,
        )
    )
    cash_for_tax += _to_decimal(period_clearance_result.scalar())

    # 周期内日常支出
    cash_for_daily_result = await db.execute(
        select(func.coalesce(func.sum(TransactionRecord.amount), 0))
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
            SELECT TO_CHAR(sale_date, 'YYYY-MM') AS month, SUM(net_amount + commission) AS revenue
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
            func.sum(WholeFishSale.net_amount + WholeFishSale.commission).label("amount"),
        )
        .where(WholeFishSale.sale_date >= sdt, WholeFishSale.sale_date <= edt)
        .group_by(WholeFishSale.customer_id)
        .order_by(func.sum(WholeFishSale.net_amount + WholeFishSale.commission).desc())
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


# ==================== 往来对账单 ====================

@router.get("/netting-statements", response_model=NettingStatementResponse)
async def list_netting_statements(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=500),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    company_id: int | None = Query(None, description="按公司筛选"),
    db: AsyncSession = Depends(get_db),
):
    """
    往来对账单 - 应收应付综合

    同时查询一家公司（或所有公司）的应收和应付，计算往来净额：
    - netting = 应收期末 - 应付期末
    - > 0: 对方欠我钱（净应收）
    - < 0: 我欠对方钱（净应付）

    支持既是客户又是供应商的公司（如：上海市海信食品有限公司）
    """
    from datetime import datetime as _dt

    from sqlalchemy import distinct

    # 日期处理：不传则查全部
    start = None
    end = None
    if start_date:
        start = _dt.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        end = _dt.strptime(end_date, "%Y-%m-%d").date()

    # 获取所有有交易记录的公司ID（销售 + 采购 + 国内采购V2）
    sale_ids_result = await db.execute(
        select(distinct(WholeFishSale.customer_id)).where(WholeFishSale.customer_id.isnot(None))
    )
    fp_sale_ids_result = await db.execute(
        select(distinct(FinishedProductSale.customer_id)).where(FinishedProductSale.customer_id.isnot(None))
    )
    fp_v2_sale_customers_result = await db.execute(
        select(distinct(FinishedProductSaleV2.customer)).where(FinishedProductSaleV2.customer.isnot(None))
    )
    fp_v2_customers = [r[0] for r in fp_v2_sale_customers_result.all() if r[0]]
    fp_v2_company_ids = set()
    if fp_v2_customers:
        v2_company_result = await db.execute(
            select(Company.id).where(Company.name.in_(fp_v2_customers))
        )
        fp_v2_company_ids = set(r[0] for r in v2_company_result.all() if r[0])

    inv_supplier_ids_result = await db.execute(
        select(distinct(ImportInvoice.supplier_id)).where(ImportInvoice.supplier_id.isnot(None))
    )
    domestic_po_ids_result = await db.execute(
        select(distinct(PurchaseOrder.supplier_id)).where(PurchaseOrder.supplier_id.isnot(None))
    )
    domestic_v2_ids_result = await db.execute(
        select(distinct(PurchaseOrderV2.supplier_id)).where(PurchaseOrderV2.supplier_id.isnot(None))
    )
    material_supplier_ids_result = await db.execute(
        select(distinct(MaterialPurchaseOrder.supplier_id)).where(MaterialPurchaseOrder.supplier_id.isnot(None))
    )

    all_company_ids = set()
    all_company_ids.update([r[0] for r in sale_ids_result.all() if r[0]])
    all_company_ids.update([r[0] for r in fp_sale_ids_result.all() if r[0]])
    all_company_ids.update(fp_v2_company_ids)
    all_company_ids.update([r[0] for r in inv_supplier_ids_result.all() if r[0]])
    all_company_ids.update([r[0] for r in domestic_po_ids_result.all() if r[0]])
    all_company_ids.update([r[0] for r in domestic_v2_ids_result.all() if r[0]])
    all_company_ids.update([r[0] for r in material_supplier_ids_result.all() if r[0]])

    if company_id:
        company_query = select(Company).where(Company.id == company_id)
    elif all_company_ids:
        company_query = select(Company).where(Company.id.in_(all_company_ids)).order_by(Company.name)
    else:
        return NettingStatementResponse(
            total=0, items=[], skip=skip, limit=limit,
            start_date=start_date, end_date=end_date,
            total_net_receivable=Decimal("0"), total_net_payable=Decimal("0"),
        )

    company_result = await db.execute(company_query)
    companies = company_result.scalars().all()

    items: list[NettingStatementItem] = []
    total_net_receivable = Decimal("0")
    total_net_payable = Decimal("0")

    for company in companies:
        # ========== 应收端计算 ==========
        sales_result = await db.execute(
            select(WholeFishSale).options(selectinload(WholeFishSale.items)).where(WholeFishSale.customer_id == company.id)
        )
        all_wf_sales = sales_result.scalars().all()

        fp_sales_result = await db.execute(
            select(FinishedProductSale).where(FinishedProductSale.customer_id == company.id)
        )
        all_fp_sales = fp_sales_result.scalars().all()

        # 以销定采 V2 销售单（按客户名称匹配）
        fp_v2_sales_result = await db.execute(
            select(FinishedProductSaleV2).options(selectinload(FinishedProductSaleV2.products)).where(FinishedProductSaleV2.customer == company.name)
        )
        all_fp_v2_sales = fp_v2_sales_result.scalars().all()

        wf_receipts_result = await db.execute(
            select(SalesReceipt)
            .options(selectinload(SalesReceipt.transaction))
            .join(WholeFishSale, SalesReceipt.sale_id == WholeFishSale.id)
            .where(WholeFishSale.customer_id == company.id)
        )
        all_wf_receipts = wf_receipts_result.scalars().all()

        fp_receipts_result = await db.execute(
            select(FinishedProductReceipt)
            .options(selectinload(FinishedProductReceipt.transaction))
            .join(FinishedProductSale, FinishedProductReceipt.sale_id == FinishedProductSale.id)
            .where(FinishedProductSale.customer_id == company.id)
        )
        all_fp_receipts = fp_receipts_result.scalars().all()

        # 以销定采 V2 收款
        fp_v2_receipts_result = await db.execute(
            select(FinishedProductReceipt)
            .options(selectinload(FinishedProductReceipt.transaction))
            .join(FinishedProductSaleV2, FinishedProductReceipt.sale_v2_id == FinishedProductSaleV2.id)
            .where(FinishedProductSaleV2.customer == company.name)
        )
        all_fp_v2_receipts = fp_v2_receipts_result.scalars().all()

        # 预查询售后退款和预付款（期初和本期都需要）
        refund_tx_result = await db.execute(
            select(TransactionRecord)
            .where(TransactionRecord.counterparty_id == company.id)
            .where(TransactionRecord.type == "expense")
            .where(TransactionRecord.category == "sales_refund")
            .where(TransactionRecord.is_confirmed.is_(True))
        )
        refund_txs = refund_tx_result.scalars().all()

        prepayment_tx_result = await db.execute(
            select(TransactionRecord)
            .where(TransactionRecord.counterparty_id == company.id)
            .where(TransactionRecord.type == "income")
            .where(TransactionRecord.category == "customer_deposit")
            .where(TransactionRecord.is_confirmed.is_(True))
        )
        prepayment_txs = prepayment_tx_result.scalars().all()

        return_orders_result = await db.execute(
            select(ReturnOrder)
            .where(ReturnOrder.customer_id == company.id)
            .where(ReturnOrder.status == "completed")
        )
        all_return_orders = return_orders_result.scalars().all()

        # 辅助函数：优先使用交易流水日期
        def _txn_date(receipt):
            """优先使用交易流水日期，更准确（支持用户修改后同步）"""
            return receipt.transaction.transaction_date if receipt.transaction else receipt.receipt_date

        # 应收期初（推导法：截至start之前的销售净额 - 截至start之前的真实收款）
        receivable_opening = Decimal("0")
        if start:
            for s in all_wf_sales:
                if s.sale_date < start:
                    receivable_opening += _to_decimal(s.net_amount)
            for s in all_fp_sales:
                if s.sale_date < start:
                    receivable_opening += _to_decimal(s.net_amount)
            for s in all_fp_v2_sales:
                if s.sale_date < start:
                    receivable_opening += _to_decimal(s.net_amount)
            # 减去截至start之前的真实收款（过滤 balance，使用 transaction_date 优先，去重）
            processed_opening_txns = set()
            for r in all_wf_receipts:
                if r.payment_method != 'balance' and _txn_date(r) < start:
                    if r.transaction_id:
                        if r.transaction_id not in processed_opening_txns:
                            processed_opening_txns.add(r.transaction_id)
                            receivable_opening -= _to_decimal(r.transaction.amount if r.transaction else r.amount)
                    else:
                        receivable_opening -= _to_decimal(r.amount)
            for r in all_fp_receipts:
                if r.payment_method != 'balance' and _txn_date(r) < start:
                    if r.transaction_id:
                        if r.transaction_id not in processed_opening_txns:
                            processed_opening_txns.add(r.transaction_id)
                            receivable_opening -= _to_decimal(r.transaction.amount if r.transaction else r.amount)
                    else:
                        receivable_opening -= _to_decimal(r.amount)
            for r in all_fp_v2_receipts:
                if r.payment_method != 'balance' and _txn_date(r) < start:
                    if r.transaction_id:
                        if r.transaction_id not in processed_opening_txns:
                            processed_opening_txns.add(r.transaction_id)
                            receivable_opening -= _to_decimal(r.transaction.amount if r.transaction else r.amount)
                    else:
                        receivable_opening -= _to_decimal(r.amount)
            # 期初之前的预付款（预付款也冲减应收）
            for txn in prepayment_txs:
                if txn.transaction_date < start:
                    receivable_opening -= _to_decimal(txn.amount)
            # 期初之前的退款（退款增加应收）
            for tx in refund_txs:
                if tx.transaction_date < start:
                    receivable_opening += _to_decimal(tx.amount)
            for r in all_return_orders:
                if r.return_date < start and r.refund_method and r.refund_method.value == "direct_refund":
                    receivable_opening += _to_decimal(r.refund_amount)

        # 应收本期销售
        receivable_current_sales = Decimal("0")
        for s in all_wf_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                receivable_current_sales += _to_decimal(s.net_amount)
        for s in all_fp_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                receivable_current_sales += _to_decimal(s.net_amount)
        for s in all_fp_v2_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                receivable_current_sales += _to_decimal(s.net_amount)

        # 应收本期收款（过滤 balance，使用 transaction_date 优先，去重 transaction_id）
        receivable_current_receipts = Decimal("0")
        processed_current_txns = set()
        for r in all_wf_receipts:
            if r.payment_method != 'balance' and (start is None or _txn_date(r) >= start) and (end is None or _txn_date(r) <= end):
                if r.transaction_id:
                    if r.transaction_id not in processed_current_txns:
                        processed_current_txns.add(r.transaction_id)
                        receivable_current_receipts += _to_decimal(r.transaction.amount if r.transaction else r.amount)
                else:
                    receivable_current_receipts += _to_decimal(r.amount)
        for r in all_fp_receipts:
            if r.payment_method != 'balance' and (start is None or _txn_date(r) >= start) and (end is None or _txn_date(r) <= end):
                if r.transaction_id:
                    if r.transaction_id not in processed_current_txns:
                        processed_current_txns.add(r.transaction_id)
                        receivable_current_receipts += _to_decimal(r.transaction.amount if r.transaction else r.amount)
                else:
                    receivable_current_receipts += _to_decimal(r.amount)
        for r in all_fp_v2_receipts:
            if r.payment_method != 'balance' and (start is None or _txn_date(r) >= start) and (end is None or _txn_date(r) <= end):
                if r.transaction_id:
                    if r.transaction_id not in processed_current_txns:
                        processed_current_txns.add(r.transaction_id)
                        receivable_current_receipts += _to_decimal(r.transaction.amount if r.transaction else r.amount)
                else:
                    receivable_current_receipts += _to_decimal(r.amount)

        # 客户预付款也计入本期收款（冲减应收）
        for txn in prepayment_txs:
            if (start is None or txn.transaction_date >= start) and (end is None or txn.transaction_date <= end):
                receivable_current_receipts += _to_decimal(txn.amount)

        # 售后退款（减少已收款，即增加应收）
        for tx in refund_txs:
            if (start is None or tx.transaction_date >= start) and (end is None or tx.transaction_date <= end):
                receivable_current_receipts -= _to_decimal(tx.amount)

        # ReturnOrder 直接退款（未走交易流水的情况）
        for r in all_return_orders:
            if (start is None or r.return_date >= start) and (end is None or r.return_date <= end):
                if r.refund_method and r.refund_method.value == "direct_refund":
                    receivable_current_receipts -= _to_decimal(r.refund_amount)

        # 应收期末（推导值，确保勾稽关系：期末 = 期初 + 本期销售 - 本期收款）
        receivable_closing = receivable_opening + receivable_current_sales - receivable_current_receipts

        # ========== 应付端计算 ==========
        invoice_result = await db.execute(
            select(ImportInvoice).options(selectinload(ImportInvoice.products)).where(ImportInvoice.supplier_id == company.id)
        )
        all_invoices = invoice_result.scalars().all()

        domestic_po_result = await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.supplier_id == company.id)
        )
        all_domestic_pos = domestic_po_result.scalars().all()

        # 预加载国内采购单（PurchaseOrder）产品明细
        po_items_map = {}
        if all_domestic_pos:
            po_ids = [po.id for po in all_domestic_pos]
            po_items_result = await db.execute(
                select(PurchaseOrderItem, Product)
                .join(Product, PurchaseOrderItem.product_id == Product.id, isouter=True)
                .where(PurchaseOrderItem.order_id.in_(po_ids))
            )
            for item, product in po_items_result.all():
                po_items_map.setdefault(item.order_id, []).append((item, product))

        domestic_v2_result = await db.execute(
            select(PurchaseOrderV2).options(selectinload(PurchaseOrderV2.products)).where(PurchaseOrderV2.supplier_id == company.id)
        )
        all_domestic_v2 = domestic_v2_result.scalars().all()

        material_po_result = await db.execute(
            select(MaterialPurchaseOrder).options(selectinload(MaterialPurchaseOrder.items)).where(MaterialPurchaseOrder.supplier_id == company.id)
        )
        all_material_pos = material_po_result.scalars().all()

        invoice_ids = [inv.id for inv in all_invoices]
        exchange_result = await db.execute(
            select(ExchangeRecord).where(ExchangeRecord.invoice_id.in_(invoice_ids))
        )
        all_exchanges = exchange_result.scalars().all()

        # 国内采购付款（TransactionRecord）
        domestic_payment_result = await db.execute(
            select(TransactionRecord)
            .where(TransactionRecord.counterparty_id == company.id)
            .where(TransactionRecord.type == "expense")
            .where(TransactionRecord.category == "goods_payment")
        )
        all_domestic_payments = domestic_payment_result.scalars().all()

        # 辅料采购付款（TransactionRecord）
        material_payment_result = await db.execute(
            select(TransactionRecord)
            .where(TransactionRecord.counterparty_id == company.id)
            .where(TransactionRecord.type == "expense")
            .where(TransactionRecord.category == "packaging_consumables")
        )
        all_material_payments = material_payment_result.scalars().all()

        is_usd = (company.currency or "CNY") == "USD"

        # 应付期初
        payable_opening = Decimal("0")
        for inv in all_invoices:
            if start is not None and inv.invoice_date < start:
                prod_result = await db.execute(select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id))
                prods = prod_result.scalars().all()
                amount_usd = sum(_to_decimal(p.total_amount) for p in prods) or _to_decimal(inv.total_amount_usd)
                if is_usd:
                    payable_opening += amount_usd
                else:
                    ex = await _get_invoice_exchange(db, inv.id, None)
                    rate = _to_decimal(ex.exchange_rate) if ex else Decimal("7.0")
                    payable_opening += amount_usd * (rate or Decimal("7.0"))

        for po in all_domestic_pos:
            if start is not None and po.order_date < start:
                payable_opening += _to_decimal(po.total_amount) - _to_decimal(po.after_sales_adjustment if hasattr(po, 'after_sales_adjustment') else 0)

        for po in all_domestic_v2:
            if start is not None and po.purchase_date < start:
                payable_opening += _to_decimal(po.total_amount) - _to_decimal(po.after_sales_adjustment)

        for po in all_material_pos:
            if start is not None and po.order_date < start:
                payable_opening += _to_decimal(po.actual_total) - _to_decimal(po.after_sales_adjustment)

        if is_usd:
            opening_payments = sum(_to_decimal(ex.amount_usd) for ex in all_exchanges if start is not None and ex.exchange_date < start)
        else:
            opening_payments = sum(_to_decimal(ex.amount_cny) for ex in all_exchanges if start is not None and ex.exchange_date < start)
        # 减去国内采购付款的期初部分
        for t in all_domestic_payments:
            if start is not None and t.transaction_date < start:
                opening_payments += _to_decimal(t.amount)
        # 减去辅料采购付款的期初部分
        for t in all_material_payments:
            if start is not None and t.transaction_date < start:
                opening_payments += _to_decimal(t.amount)
        payable_opening -= opening_payments

        # 应付本期采购
        payable_current_purchase = Decimal("0")
        for inv in all_invoices:
            if (start is None or inv.invoice_date >= start) and (end is None or inv.invoice_date <= end):
                prod_result = await db.execute(select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id))
                prods = prod_result.scalars().all()
                amount_usd = sum(_to_decimal(p.total_amount) for p in prods) or _to_decimal(inv.total_amount_usd)
                ex = await _get_invoice_exchange(db, inv.id, None)
                rate = _to_decimal(ex.exchange_rate) if ex else Decimal("7.0")
                payable_current_purchase += amount_usd * (rate or Decimal("7.0"))

        for po in all_domestic_pos:
            if (start is None or po.order_date >= start) and (end is None or po.order_date <= end):
                payable_current_purchase += _to_decimal(po.total_amount) - _to_decimal(po.after_sales_adjustment if hasattr(po, 'after_sales_adjustment') else 0)

        for po in all_domestic_v2:
            if (start is None or po.purchase_date >= start) and (end is None or po.purchase_date <= end):
                payable_current_purchase += _to_decimal(po.total_amount) - _to_decimal(po.after_sales_adjustment)

        for po in all_material_pos:
            if (start is None or po.order_date >= start) and (end is None or po.order_date <= end):
                payable_current_purchase += _to_decimal(po.actual_total) - _to_decimal(po.after_sales_adjustment)

        # 应付本期付款（购汇 + 国内采购付款）
        if is_usd:
            payable_current_payments = sum(_to_decimal(ex.amount_usd) for ex in all_exchanges if (start is None or ex.exchange_date >= start) and (end is None or ex.exchange_date <= end))
        else:
            payable_current_payments = sum(
                _to_decimal(ex.amount_cny) + _to_decimal(ex.fee_cny)
                for ex in all_exchanges if (start is None or ex.exchange_date >= start) and (end is None or ex.exchange_date <= end)
            )
        # 加上国内采购付款（TransactionRecord goods_payment）
        for t in all_domestic_payments:
            if (start is None or t.transaction_date >= start) and (end is None or t.transaction_date <= end):
                payable_current_payments += _to_decimal(t.amount)

        # 加上辅料采购付款（TransactionRecord packaging_consumables）
        for t in all_material_payments:
            if (start is None or t.transaction_date >= start) and (end is None or t.transaction_date <= end):
                payable_current_payments += _to_decimal(t.amount)

        # 应付期末
        payable_closing = payable_opening + payable_current_purchase - payable_current_payments

        # 往来净额
        netting_opening = receivable_opening - payable_opening
        netting_closing = receivable_closing - payable_closing

        if netting_closing > 0:
            netting_direction = "应收"
        elif netting_closing < 0:
            netting_direction = "应付"
        else:
            netting_direction = "平"

        # 如果没有任何交易，跳过
        if (receivable_closing == 0 and payable_closing == 0 and
            receivable_current_sales == 0 and payable_current_purchase == 0):
            continue

        # ========== 预查询产品/批次名称 ==========
        # 整鱼销售的批次名称、宰杀日期、加工厂EU编号
        wf_batch_ids = {s.batch_id for s in all_wf_sales if s.batch_id}
        wf_batch_map = {}
        wf_batch_extra = {}
        if wf_batch_ids:
            batch_result = await db.execute(select(Batch.id, Batch.batch_name).where(Batch.id.in_(wf_batch_ids)))
            wf_batch_map = {r[0]: r[1] for r in batch_result.all()}

            batch_extra_result = await db.execute(
                select(BatchInvoice.batch_id, ImportInvoice.kill_date, Company.code)
                .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
                .join(Company, ImportInvoice.processing_plant_id == Company.id, isouter=True)
                .where(BatchInvoice.batch_id.in_(wf_batch_ids))
            )
            batch_extra_raw: dict[int, dict] = {}
            for batch_id, kill_date, plant_code in batch_extra_result.all():
                d = batch_extra_raw.setdefault(batch_id, {"kill_dates": [], "plant_codes": []})
                if kill_date:
                    d["kill_dates"].append(kill_date)
                if plant_code:
                    d["plant_codes"].append(plant_code)
            wf_batch_extra = {
                bid: {
                    "slaughter_date": min(d["kill_dates"]) if d["kill_dates"] else None,
                    "processing_plant_code": d["plant_codes"][0] if d["plant_codes"] else None,
                }
                for bid, d in batch_extra_raw.items()
            }

        # 旧版成品销售的产品名称
        fp_product_ids = {s.product_id for s in all_fp_sales if s.product_id}
        fp_product_map = {}
        if fp_product_ids:
            prod_result = await db.execute(select(Product.id, Product.name).where(Product.id.in_(fp_product_ids)))
            fp_product_map = {r[0]: r[1] for r in prod_result.all()}

        # ========== 构建销售明细（按规格展开）==========
        sale_details = []
        for s in all_wf_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                wf_items = s.items or []
                batch_extra = wf_batch_extra.get(s.batch_id, {})
                if wf_items:
                    total_gross = sum(_to_decimal(item.amount) for item in wf_items)
                    total_after = _to_decimal(s.after_sales_adjustment)
                    total_discount = _to_decimal(s.discount)
                    for item in wf_items:
                        item_amount = _to_decimal(item.amount)
                        ratio = item_amount / total_gross if total_gross else Decimal("0")
                        item_after = total_after * ratio
                        item_discount = total_discount * ratio
                        sale_details.append(ReceivableSaleItem(
                            date=s.sale_date,
                            sale_no=s.sale_no,
                            product_name="三文鱼",
                            batch_name=wf_batch_map.get(s.batch_id, None),
                            slaughter_date=batch_extra.get("slaughter_date"),
                            processing_plant_code=batch_extra.get("processing_plant_code"),
                            spec=item.spec or s.spec or "整鱼",
                            quantity=item.box_count,
                            weight_kg=item.weight_kg,
                            unit_price=item.unit_price,
                            gross_amount=item_amount,
                            after_sales_adjustment=item_after,
                            discount=item_discount,
                            net_amount=item_amount - item_after - item_discount,
                        ))
                else:
                    # 无规格明细时退回到主单
                    sale_details.append(ReceivableSaleItem(
                        date=s.sale_date,
                        sale_no=s.sale_no,
                        product_name="三文鱼",
                        batch_name=wf_batch_map.get(s.batch_id, None),
                        slaughter_date=batch_extra.get("slaughter_date"),
                        processing_plant_code=batch_extra.get("processing_plant_code"),
                        spec=s.spec or "整鱼",
                        quantity=s.box_count,
                        weight_kg=s.weight_kg,
                        unit_price=s.unit_price,
                        gross_amount=_to_decimal(s.gross_amount),
                        after_sales_adjustment=_to_decimal(s.after_sales_adjustment),
                        discount=_to_decimal(s.discount),
                        net_amount=_to_decimal(s.net_amount),
                    ))
        for s in all_fp_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                sale_details.append(ReceivableSaleItem(
                    date=s.sale_date,
                    sale_no=f"FP-{s.id}",
                    product_name=fp_product_map.get(s.product_id, None),
                    batch_name=None,
                    spec="成品",
                    quantity=s.quantity,
                    weight_kg=s.total_weight_kg,
                    unit_price=s.unit_price,
                    gross_amount=_to_decimal(s.gross_amount),
                    after_sales_adjustment=_to_decimal(s.after_sales_adjustment),
                    discount=_to_decimal(s.discount),
                    net_amount=_to_decimal(s.net_amount),
                ))
        for s in all_fp_v2_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                products = s.products or []
                if products:
                    total_gross = sum(_to_decimal(p.total_amount) for p in products)
                    total_after = _to_decimal(s.after_sales_adjustment)
                    total_discount = _to_decimal(s.discount)
                    for p in products:
                        item_amount = _to_decimal(p.total_amount)
                        ratio = item_amount / total_gross if total_gross else Decimal("0")
                        item_after = total_after * ratio
                        item_discount = total_discount * ratio
                        sale_details.append(ReceivableSaleItem(
                            date=s.sale_date,
                            sale_no=s.sale_no,
                            product_name=p.product_name or s.product_name,
                            batch_name=s.batch_no,
                            spec=p.product_spec or s.product_name or "成品",
                            quantity=p.box_count,
                            weight_kg=p.weight_kg,
                            unit_price=p.unit_price,
                            gross_amount=item_amount,
                            after_sales_adjustment=item_after,
                            discount=item_discount,
                            net_amount=item_amount - item_after - item_discount,
                        ))
                else:
                    sale_details.append(ReceivableSaleItem(
                        date=s.sale_date,
                        sale_no=s.sale_no,
                        product_name=s.product_name,
                        batch_name=s.batch_no,
                        spec=s.product_name or "成品",
                        quantity=s.quantity,
                        weight_kg=s.weight,
                        unit_price=s.unit_price,
                        gross_amount=_to_decimal(s.total_amount),
                        after_sales_adjustment=_to_decimal(s.after_sales_adjustment),
                        discount=_to_decimal(s.discount),
                        net_amount=_to_decimal(s.net_amount),
                    ))
        sale_details.sort(key=lambda x: x.date)

        # ========== 构建折扣明细 ==========
        discount_details = []
        for s in all_wf_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                if s.discount and s.discount > 0:
                    discount_details.append(ReceivableDiscountItem(
                        date=s.sale_date,
                        sale_no=s.sale_no,
                        discount_amount=_to_decimal(s.discount),
                        reason=None,
                    ))
        for s in all_fp_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                if s.discount and s.discount > 0:
                    discount_details.append(ReceivableDiscountItem(
                        date=s.sale_date,
                        sale_no=f"FP-{s.id}",
                        discount_amount=_to_decimal(s.discount),
                        reason=None,
                    ))
        for s in all_fp_v2_sales:
            if (start is None or s.sale_date >= start) and (end is None or s.sale_date <= end):
                if s.discount and s.discount > 0:
                    discount_details.append(ReceivableDiscountItem(
                        date=s.sale_date,
                        sale_no=s.sale_no,
                        discount_amount=_to_decimal(s.discount),
                        reason=None,
                    ))
        discount_details.sort(key=lambda x: x.date)

        # ========== 构建售后明细（销售）==========
        aftersales_details = []
        # ReturnOrder 销售退货
        return_orders_result = await db.execute(
            select(ReturnOrder)
            .where(ReturnOrder.customer_id == company.id)
            .where(ReturnOrder.status == "completed")
        )
        all_return_orders = return_orders_result.scalars().all()
        for r in all_return_orders:
            if (start is None or r.return_date >= start) and (end is None or r.return_date <= end):
                sale_no = None
                if r.whole_fish_sale_id:
                    sale = next((s for s in all_wf_sales if s.id == r.whole_fish_sale_id), None)
                    if sale:
                        sale_no = sale.sale_no
                return_items_result = await db.execute(
                    select(ReturnItem).where(ReturnItem.return_order_id == r.id)
                )
                return_items = return_items_result.scalars().all()
                item = return_items[0] if return_items else None
                aftersales_details.append(ReceivableAftersalesItem(
                    date=r.return_date,
                    return_no=r.return_no,
                    sale_no=sale_no,
                    quantity=float(item.weight_kg) if item else None,
                    unit_price=_to_decimal(item.unit_price) if item else None,
                    amount=_to_decimal(r.refund_amount),
                    reason=item.remarks if item else r.problem_description,
                    refund_method=r.refund_method.value if r.refund_method else None,
                ))
        aftersales_details.sort(key=lambda x: x.date)

        # ========== 构建采购售后明细 ==========
        purchase_return_result = await db.execute(
            select(PurchaseReturnOrder)
            .where(PurchaseReturnOrder.supplier_id == company.id)
            .where(PurchaseReturnOrder.status == "completed")
        )
        all_purchase_returns = purchase_return_result.scalars().all()
        purchase_return_details = []
        for pr in all_purchase_returns:
            if (start is None or pr.return_date >= start) and (end is None or pr.return_date <= end):
                purchase_return_details.append({
                    "date": pr.return_date,
                    "return_no": pr.return_no,
                    "amount": float(_to_decimal(pr.refund_amount)),
                    "reason": pr.problem_description,
                    "refund_method": pr.refund_method.value if pr.refund_method else None,
                })
        purchase_return_details.sort(key=lambda x: x["date"])

        # ========== 构建采购明细（按产品明细展开） ==========
        purchase_details = []
        for inv in all_invoices:
            if (start is None or inv.invoice_date >= start) and (end is None or inv.invoice_date <= end):
                prods = inv.products or []
                ex = await _get_invoice_exchange(db, inv.id, None)
                rate = _to_decimal(ex.exchange_rate) if ex else Decimal("7.0")
                if not prods:
                    amount_usd = _to_decimal(inv.total_amount_usd)
                    amount_cny = amount_usd * (rate or Decimal("7.0"))
                    purchase_details.append(PayablePurchaseItem(
                        date=inv.invoice_date,
                        invoice_no=inv.invoice_no,
                        product_name=None,
                        spec=None,
                        batch_no=None,
                        quantity=None,
                        weight_kg=None,
                        unit_price=None,
                        amount_usd=amount_usd,
                        exchange_rate=rate,
                        amount_cny=round(amount_cny, 2),
                        after_sales_adjustment=Decimal("0"),
                    ))
                else:
                    for p in prods:
                        p_amount_usd = _to_decimal(p.total_amount)
                        p_amount_cny = p_amount_usd * (rate or Decimal("7.0"))
                        purchase_details.append(PayablePurchaseItem(
                            date=inv.invoice_date,
                            invoice_no=inv.invoice_no,
                            product_name=p.product_name,
                            spec=p.product_spec,
                            batch_no=None,
                            quantity=p.box_count,
                            weight_kg=p.net_weight_kg,
                            unit_price=p.unit_price,
                            amount_usd=p_amount_usd,
                            exchange_rate=rate,
                            amount_cny=round(p_amount_cny, 2),
                            after_sales_adjustment=Decimal("0"),
                        ))
        for po in all_domestic_pos:
            if (start is None or po.order_date >= start) and (end is None or po.order_date <= end):
                po_after = _to_decimal(po.after_sales_adjustment) if hasattr(po, 'after_sales_adjustment') else Decimal("0")
                total_po_amount = _to_decimal(po.total_amount)
                line_items = po_items_map.get(po.id, [])
                if not line_items:
                    purchase_details.append(PayablePurchaseItem(
                        date=po.order_date,
                        invoice_no=po.order_no or f"PO-{po.id}",
                        product_name=None,
                        spec=None,
                        batch_no=None,
                        quantity=None,
                        weight_kg=None,
                        unit_price=None,
                        amount_usd=Decimal("0"),
                        amount_cny=round(total_po_amount, 2),
                        after_sales_adjustment=po_after,
                    ))
                else:
                    for item, product in line_items:
                        item_amount = _to_decimal(item.total_amount)
                        ratio = item_amount / total_po_amount if total_po_amount else Decimal("0")
                        item_after = po_after * ratio
                        purchase_details.append(PayablePurchaseItem(
                            date=po.order_date,
                            invoice_no=po.order_no or f"PO-{po.id}",
                            product_name=product.name if product else None,
                            spec=product.spec if product else None,
                            batch_no=None,
                            quantity=int(item.qty) if item.qty is not None else None,
                            weight_kg=item.qty,
                            unit_price=item.unit_price,
                            amount_usd=Decimal("0"),
                            amount_cny=round(item_amount, 2),
                            after_sales_adjustment=round(item_after, 2),
                        ))
        for po in all_domestic_v2:
            if (start is None or po.purchase_date >= start) and (end is None or po.purchase_date <= end):
                po_after = _to_decimal(po.after_sales_adjustment) if hasattr(po, 'after_sales_adjustment') else Decimal("0")
                total_po_amount = _to_decimal(po.total_amount)
                products = po.products or []
                if not products:
                    purchase_details.append(PayablePurchaseItem(
                        date=po.purchase_date,
                        invoice_no=po.purchase_no or f"PO-{po.id}",
                        product_name=None,
                        spec=None,
                        batch_no=None,
                        quantity=None,
                        weight_kg=None,
                        unit_price=None,
                        amount_usd=Decimal("0"),
                        amount_cny=round(total_po_amount, 2),
                        after_sales_adjustment=po_after,
                    ))
                else:
                    for p in products:
                        p_amount = _to_decimal(p.total_amount)
                        ratio = p_amount / total_po_amount if total_po_amount else Decimal("0")
                        p_after = po_after * ratio
                        purchase_details.append(PayablePurchaseItem(
                            date=po.purchase_date,
                            invoice_no=po.purchase_no or f"PO-{po.id}",
                            product_name=p.product_name,
                            spec=p.product_spec,
                            batch_no=p.batch,
                            quantity=p.box_count,
                            weight_kg=p.weight_kg,
                            unit_price=p.unit_price,
                            amount_usd=Decimal("0"),
                            amount_cny=round(p_amount, 2),
                            after_sales_adjustment=round(p_after, 2),
                        ))
        for po in all_material_pos:
            if (start is None or po.order_date >= start) and (end is None or po.order_date <= end):
                po_after = _to_decimal(po.after_sales_adjustment)
                total_po_amount = _to_decimal(po.actual_total)
                material_items = po.items or []
                if not material_items:
                    purchase_details.append(PayablePurchaseItem(
                        date=po.order_date,
                        invoice_no=po.order_no,
                        product_name="辅料采购",
                        spec=None,
                        batch_no=None,
                        quantity=None,
                        weight_kg=None,
                        unit_price=None,
                        amount_usd=Decimal("0"),
                        amount_cny=round(total_po_amount, 2),
                        after_sales_adjustment=po_after,
                    ))
                else:
                    for item in material_items:
                        p_amount = _to_decimal(item.actual_amount)
                        ratio = p_amount / total_po_amount if total_po_amount else Decimal("0")
                        item_after = po_after * ratio
                        product_name = item.product.name if item.product else None
                        spec = item.product.spec if item.product else None
                        purchase_details.append(PayablePurchaseItem(
                            date=po.order_date,
                            invoice_no=po.order_no,
                            product_name=product_name,
                            spec=spec,
                            batch_no=None,
                            quantity=item.box_count if item.box_count is not None else None,
                            weight_kg=None,
                            unit_price=item.actual_unit_price,
                            amount_usd=Decimal("0"),
                            amount_cny=round(p_amount, 2),
                            after_sales_adjustment=round(item_after, 2),
                        ))
        purchase_details.sort(key=lambda x: x.date)

        # ========== 构建收支明细（从交易流水获取，排除对冲结算内部记录）==========
        payment_details = []
        
        # 查询与客户相关的实际交易流水记录（排除余额抵扣等虚拟交易，保留对冲结算）
        txn_result = await db.execute(
            select(TransactionRecord)
            .where(TransactionRecord.counterparty_id == company.id)
            .where(TransactionRecord.category != "balance_deduction")
            .where(TransactionRecord.is_confirmed)
        )
        all_txn = txn_result.scalars().all()
        
        for t in all_txn:
            if (start is None or t.transaction_date >= start) and (end is None or t.transaction_date <= end):
                txn_type = "receipt" if t.type == "income" else "payment"
                description = t.category
                if t.category == "customer_deposit":
                    description = "客户预付款"
                elif t.category == "goods_payment":
                    description = "采购付款"
                elif t.category == "packaging_consumables":
                    description = "辅料采购付款"
                elif t.category == "main_business_income":
                    description = "主营业务收入"
                elif t.category == "main_business_revenue":
                    description = "主营业务收入"
                elif t.category == "other_income":
                    description = "其他收入"
                elif t.category == "other_expense":
                    description = "其他支出"
                elif t.category == "scan_fee":
                    description = "扫码费"
                elif t.category == "import_payment":
                    description = "进口付款"
                else:
                    description = t.category
                
                payment_details.append(NettingPaymentItem(
                    date=t.transaction_date,
                    description=description,
                    amount=_to_decimal(t.amount),
                    type=txn_type,
                    notes=t.description or t.reference_no,
                ))
        
        # 进口购汇付款（ExchangeRecord）
        for ex in all_exchanges:
            if (start is None or ex.exchange_date >= start) and (end is None or ex.exchange_date <= end):
                payment_details.append(NettingPaymentItem(
                    date=ex.exchange_date,
                    description="进口购汇付款",
                    amount=_to_decimal(ex.amount_cny) + _to_decimal(ex.fee_cny),
                    type="payment",
                    notes=ex.notes,
                ))
        
        payment_details.sort(key=lambda x: x.date)

        items.append(NettingStatementItem(
            company_id=company.id,
            company_name=company.name,
            company_code=company.code,
            company_type="both" if (all_wf_sales or all_fp_sales) and (all_invoices or all_domestic_pos or all_domestic_v2 or all_material_pos) else ("customer" if (all_wf_sales or all_fp_sales) else "supplier"),
            receivable_opening=round(receivable_opening, 2),
            receivable_current_sales=round(receivable_current_sales, 2),
            receivable_current_receipts=round(receivable_current_receipts, 2),
            receivable_closing=round(receivable_closing, 2),
            payable_opening=round(payable_opening, 2),
            payable_current_purchase=round(payable_current_purchase, 2),
            payable_current_expenses=Decimal("0"),
            payable_current_payments=round(payable_current_payments, 2),
            payable_closing=round(payable_closing, 2),
            netting_opening=round(netting_opening, 2),
            netting_closing=round(netting_closing, 2),
            netting_direction=netting_direction,
            sale_details=sale_details,
            discount_details=discount_details,
            aftersales_details=aftersales_details,
            purchase_details=purchase_details,
            payment_details=payment_details,
            purchase_return_details=purchase_return_details,
        ))

        if netting_closing > 0:
            total_net_receivable += netting_closing
        else:
            total_net_payable += abs(netting_closing)

    return NettingStatementResponse(
        total=len(items),
        items=items[skip:skip+limit],
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        total_net_receivable=round(total_net_receivable, 2),
        total_net_payable=round(total_net_payable, 2),
    )


# ==================== 报关行应付对账单 ====================

@router.get("/customs-broker-statements", response_model=CustomsBrokerStatementResponse)
async def list_customs_broker_statements(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    broker_id: int | None = Query(None, description="按报关行筛选"),
    db: AsyncSession = Depends(get_db),
):
    """
    报关行应付对账单

    费用来源：import_taxes + clearance_costs（import_fees 视图）
    付款来源：transaction_records (category='clearance_payment')
    """
    from datetime import datetime as _dt
    from app.schemas.report import (
        CustomsBrokerFeeItem,
        CustomsBrokerPaymentItem,
        CustomsBrokerStatementItem,
    )

    today = _dt.now().date()
    if not start_date:
        start_date = "2000-01-01"
    if not end_date:
        end_date = today.isoformat()

    start = _dt.strptime(start_date, "%Y-%m-%d").date()
    end = _dt.strptime(end_date, "%Y-%m-%d").date()

    # 1. 获取所有有费用的报关行
    broker_sql = """
    SELECT DISTINCT c.id, c.name
    FROM clearance_costs cc
    JOIN companies c ON c.id = cc.customs_broker_id
    WHERE cc.customs_broker_id IS NOT NULL
    """
    if broker_id:
        broker_sql += f" AND c.id = {broker_id}"
    broker_sql += " ORDER BY c.name"

    broker_result = await db.execute(text(broker_sql))
    brokers = [(r[0], r[1]) for r in broker_result.all()]

    if not brokers:
        return CustomsBrokerStatementResponse(
            total=0, items=[],
            start_date=start_date, end_date=end_date,
            total_payable=Decimal("0"),
        )

    # 预加载银行账号名称映射
    bank_result = await db.execute(select(BankAccount.id, BankAccount.bank_name, BankAccount.account_number))
    bank_map = {r[0]: f"{r[1]} ({r[2]})" for r in bank_result.all()}

    items: list[CustomsBrokerStatementItem] = []
    total_payable = Decimal("0")

    for bid, bname in brokers:
        # 2. 该报关行的所有清关费记录（只取 clearance_costs，不含税费）
        fee_sql = """
        SELECT
            i.invoice_no,
            c.cost_date AS fee_date,
            c.gross_weight_kg,
            c.clearance_fee,
            c.freight_fee,
            c.inspection_fee,
            c.quarantine_fee,
            c.other_costs,
            c.total_cost AS clearance_total,
            COALESCE(c.payment_type, 'monthly') AS payment_type
        FROM import_invoices i
        JOIN clearance_costs c ON c.invoice_id = i.id
        WHERE c.customs_broker_id = :broker_id
        ORDER BY c.cost_date
        """
        fee_result = await db.execute(text(fee_sql), {"broker_id": bid})
        fee_rows = fee_result.mappings().all()

        # 3. 该报关行的所有付款记录
        payment_result = await db.execute(
            select(TransactionRecord)
            .where(
                TransactionRecord.category == "clearance_payment",
                TransactionRecord.counterparty_name == bname,
            )
            .order_by(TransactionRecord.transaction_date)
        )
        payment_rows = payment_result.scalars().all()

        # 期初/本期/期末计算（只计算清关费，不含税费）
        opening_balance = Decimal("0")
        current_fees = Decimal("0")
        current_payments = Decimal("0")

        fee_details = []
        for row in fee_rows:
            fee_date = row["fee_date"]
            clearance_total = _to_decimal(row["clearance_total"])

            if fee_date and fee_date < start:
                opening_balance += clearance_total
            elif fee_date and start <= fee_date <= end:
                current_fees += clearance_total

            if fee_date and start <= fee_date <= end:
                fee_details.append(CustomsBrokerFeeItem(
                    date=fee_date,
                    invoice_no=row["invoice_no"] or "",
                    gross_weight_kg=round(_to_decimal(row["gross_weight_kg"] or 0), 3),
                    clearance_fee=round(_to_decimal(row["clearance_fee"] or 0), 2),
                    freight_fee=round(_to_decimal(row["freight_fee"] or 0), 2),
                    inspection_fee=round(_to_decimal(row["inspection_fee"] or 0), 2),
                    quarantine_fee=round(_to_decimal(row["quarantine_fee"] or 0), 2),
                    other_costs=round(_to_decimal(row["other_costs"] or 0), 2),
                    grand_total=round(clearance_total, 2),
                    payment_type=row["payment_type"],
                ))

        payment_details = []
        for tx in payment_rows:
            tx_date = tx.transaction_date
            amount = _to_decimal(tx.amount)

            if tx_date and tx_date < start:
                opening_balance -= amount
            elif tx_date and start <= tx_date <= end:
                current_payments += amount

            if tx_date and start <= tx_date <= end:
                payment_details.append(CustomsBrokerPaymentItem(
                    date=tx_date,
                    amount=round(amount, 2),
                    reference_no=tx.reference_no,
                    description=tx.description,
                    from_account_name=bank_map.get(tx.from_account_id),
                ))

        closing_balance = opening_balance + current_fees - current_payments

        items.append(CustomsBrokerStatementItem(
            broker_id=bid,
            broker_name=bname,
            opening_balance=round(opening_balance, 2),
            current_fees=round(current_fees, 2),
            current_payments=round(current_payments, 2),
            closing_balance=round(closing_balance, 2),
            fee_details=fee_details,
            payment_details=payment_details,
        ))
        total_payable += closing_balance

    return CustomsBrokerStatementResponse(
        total=len(items),
        items=items,
        start_date=start_date,
        end_date=end_date,
        total_payable=round(total_payable, 2),
    )
