#!/usr/bin/env python3
"""Refactor reports.py: extract _calc_batch_financials and wire callers."""

FILE = "/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend/app/api/v1/endpoints/reports.py"

with open(FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

# ------------------------------------------------------------------
# Helper text to insert
# ------------------------------------------------------------------
HELPER_LINES = """\n\nasync def _calc_batch_financials(db: AsyncSession, batch) -> dict:
    \"\"\"\n    计算批次的所有财务数据（从关联发票获取到净利润计算）\n\n    Returns:\n        dict containing all financial metrics for the batch\n    \"\"\"\n    batch_id = batch.id\n\n    # 获取关联发票\n    bi_result = await db.execute(\n        select(BatchInvoice, ImportInvoice)\n        .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)\n        .where(BatchInvoice.batch_id == batch_id)\n    )\n    bi_rows = bi_result.all()\n\n    if not bi_rows:\n        return None\n\n    # 批次级销售\n    sales_list = await _get_batch_sales(db, batch_id)\n\n    total_purchase_usd = Decimal(\"0\")\n    total_weight = Decimal(\"0\")\n    total_boxes = 0\n\n    total_import_duty = Decimal(\"0\")\n    total_import_vat = Decimal(\"0\")\n    total_clearance = Decimal(\"0\")\n    total_exchange_payment = Decimal(\"0\")\n    total_exchange_fee = Decimal(\"0\")\n    exchange_rate = None\n    batch_exchange_applied = False  # 批次级购汇只计算一次\n    is_exchange_estimated = False  # 标记是否使用了估算值\n\n    # 清关费分项汇总\n    customs_broker_name = None\n    clearance_breakdown = {\n        \"customs_broker\": None,\n        \"clearance_fee\": Decimal(\"0\"),\n        \"freight_fee\": Decimal(\"0\"),\n        \"inspection_fee\": Decimal(\"0\"),\n        \"quarantine_fee\": Decimal(\"0\"),\n        \"other_costs\": Decimal(\"0\"),\n        \"extra_expenses\": Decimal(\"0\"),\n    }\n\n    invoice_details: List[dict] = []\n    invoice_nos = []\n\n    # 先计算批次总重量用于销售分配\n    batch_total_weight = Decimal(\"0\")\n    invoice_weights = {}\n    for bi, inv in bi_rows:\n        prod_result = await db.execute(\n            select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)\n        )\n        prods = prod_result.scalars().all()\n        w = sum(_to_decimal(p.net_weight_kg) for p in prods)\n        if w == 0:\n            w = _to_decimal(inv.total_weight_kg)\n        invoice_weights[inv.id] = w\n        batch_total_weight += w\n\n    # 预加载所有发票的税费和清关（避免N+1）\n    all_inv_ids = [inv.id for _, inv in bi_rows]\n    taxes_map = await _batch_get_taxes(db, all_inv_ids)\n    clearances_map = await _batch_get_clearances(db, all_inv_ids)\n\n    # 收集从票的父票ID，额外查询父票税费（用于从票分摊）\n    parent_inv_ids = [inv.parent_invoice_id for _, inv in bi_rows if inv.parent_invoice_id]\n    parent_taxes_map = {}\n    parent_clearances_map = {}\n    parent_weights_map = {}\n    if parent_inv_ids:\n        parent_taxes_map = await _batch_get_taxes(db, parent_inv_ids)\n        parent_clearances_map = await _batch_get_clearances(db, parent_inv_ids)\n        pw_result = await db.execute(\n            select(ImportInvoice.id, ImportInvoice.total_weight_kg).where(ImportInvoice.id.in_(parent_inv_ids))\n        )\n        parent_weights_map = {row[0]: _to_decimal(row[1]) for row in pw_result.all()}\n\n    # 预加载所有发票的产品（避免循环内多次查询）\n    prods_map_result = await db.execute(\n        select(InvoiceProduct).where(InvoiceProduct.invoice_id.in_(all_inv_ids))\n    )\n    prods_map = {}\n    for p in prods_map_result.scalars().all():\n        prods_map.setdefault(p.invoice_id, []).append(p)\n\n    for bi, inv in bi_rows:\n        invoice_nos.append(inv.invoice_no)\n        inv_weight = invoice_weights[inv.id]\n        prods = prods_map.get(inv.id, [])\n        inv_boxes = sum(p.box_count or 0 for p in prods)\n        if inv_boxes == 0:\n            inv_boxes = inv.total_boxes or 0\n\n        inv_amount = sum(_to_decimal(p.total_amount) for p in prods)\n        if inv_amount == 0:\n            inv_amount = _to_decimal(inv.total_amount_usd)\n\n        # 税费（从预加载字典获取，从票没有则查找父票并按重量比例分摊）\n        tax = taxes_map.get(inv.id)\n        if tax:\n            inv_duty = _to_decimal(tax.import_duty)\n            inv_vat = _to_decimal(tax.import_vat)\n        elif inv.parent_invoice_id and inv.parent_invoice_id in parent_taxes_map:\n            parent_tax = parent_taxes_map[inv.parent_invoice_id]\n            parent_w = parent_weights_map.get(inv.parent_invoice_id, Decimal(\"0\"))\n            proportion = inv_weight / parent_w if parent_w > 0 else Decimal(\"0\")\n            inv_duty = _to_decimal(parent_tax.import_duty) * proportion\n            inv_vat = _to_decimal(parent_tax.import_vat) * proportion\n        else:\n            inv_duty = Decimal(\"0\")\n            inv_vat = Decimal(\"0\")\n\n        # 清关（从预加载字典获取，从票没有则查找父票并按重量比例分摊）\n        clearance = clearances_map.get(inv.id)\n        inv_clearance = Decimal(\"0\")\n        if clearance:\n            inv_clearance = (\n                _to_decimal(clearance.clearance_fee) +\n                _to_decimal(clearance.freight_fee) +\n                _to_decimal(clearance.inspection_fee) +\n                _to_decimal(clearance.quarantine_fee) +\n                _to_decimal(clearance.other_costs)\n            )\n            clearance_breakdown[\"clearance_fee\"] += _to_decimal(clearance.clearance_fee)\n            clearance_breakdown[\"freight_fee\"] += _to_decimal(clearance.freight_fee)\n            clearance_breakdown[\"inspection_fee\"] += _to_decimal(clearance.inspection_fee)\n            clearance_breakdown[\"quarantine_fee\"] += _to_decimal(clearance.quarantine_fee)\n            clearance_breakdown[\"other_costs\"] += _to_decimal(clearance.other_costs)\n            if clearance.customs_broker and not customs_broker_name:\n                customs_broker_name = clearance.customs_broker\n                clearance_breakdown[\"customs_broker\"] = customs_broker_name\n        elif inv.parent_invoice_id and inv.parent_invoice_id in parent_clearances_map:\n            parent_clearance = parent_clearances_map[inv.parent_invoice_id]\n            parent_w = parent_weights_map.get(inv.parent_invoice_id, Decimal(\"0\"))\n            proportion = inv_weight / parent_w if parent_w > 0 else Decimal(\"0\")\n            inv_clearance = (\n                _to_decimal(parent_clearance.clearance_fee) +\n                _to_decimal(parent_clearance.freight_fee) +\n                _to_decimal(parent_clearance.inspection_fee) +\n                _to_decimal(parent_clearance.quarantine_fee) +\n                _to_decimal(parent_clearance.other_costs)\n            ) * proportion\n            clearance_breakdown[\"clearance_fee\"] += _to_decimal(parent_clearance.clearance_fee) * proportion\n            clearance_breakdown[\"freight_fee\"] += _to_decimal(parent_clearance.freight_fee) * proportion\n            clearance_breakdown[\"inspection_fee\"] += _to_decimal(parent_clearance.inspection_fee) * proportion\n            clearance_breakdown[\"quarantine_fee\"] += _to_decimal(parent_clearance.quarantine_fee) * proportion\n            clearance_breakdown[\"other_costs\"] += _to_decimal(parent_clearance.other_costs) * proportion\n            if parent_clearance.customs_broker and not customs_broker_name:\n                customs_broker_name = parent_clearance.customs_broker\n                clearance_breakdown[\"customs_broker\"] = customs_broker_name\n\n        # 购汇\n        ex = await _get_invoice_exchange(db, inv.id, batch_id)\n        inv_exchange_payment = Decimal(\"0\")\n        inv_exchange_fee = Decimal(\"0\")\n        inv_exchange_rate = Decimal(\"0\")\n        if ex and ex.amount_cny > 0:\n            if ex.invoice_id == inv.id:\n                # 发票级别购汇记录\n                inv_exchange_payment = _to_decimal(ex.amount_cny)\n                inv_exchange_fee = _to_decimal(ex.fee_cny)\n                inv_exchange_rate = _to_decimal(ex.exchange_rate)\n            elif ex.related_invoice_ids and inv.id in ex.related_invoice_ids:\n                # 合并购汇：按当前发票金额占总购汇金额的比例分摊\n                total_exchange_usd = _to_decimal(ex.amount_usd)\n                if total_exchange_usd > 0:\n                    proportion = inv_amount / total_exchange_usd\n                    inv_exchange_payment = _to_decimal(ex.amount_cny) * proportion\n                    inv_exchange_fee = _to_decimal(ex.fee_cny) * proportion\n                    inv_exchange_rate = _to_decimal(ex.exchange_rate)\n            elif not batch_exchange_applied:\n                # 批次级别购汇记录，只计算一次\n                inv_exchange_payment = _to_decimal(ex.amount_cny)\n                inv_exchange_fee = _to_decimal(ex.fee_cny)\n                inv_exchange_rate = _to_decimal(ex.exchange_rate)\n                batch_exchange_applied = True\n        else:\n            # 无购汇记录或空记录 → 批次财报估算：汇率=6.8，手续费=150+0.1%×CNY\n            inv_exchange_rate = Decimal(\"6.8\")\n            inv_exchange_payment = inv_amount * inv_exchange_rate\n            inv_exchange_fee = Decimal(\"150\") / len(bi_rows) + inv_exchange_payment * Decimal(\"0.001\")\n            is_exchange_estimated = True\n\n        if exchange_rate is None or exchange_rate == 0:\n            if inv_exchange_rate > 0:\n                exchange_rate = inv_exchange_rate\n\n        # 汇总\n        total_purchase_usd += inv_amount\n        total_weight += inv_weight\n        total_boxes += inv_boxes\n        total_import_duty += inv_duty\n        total_import_vat += inv_vat\n        total_clearance += inv_clearance\n        total_exchange_payment += inv_exchange_payment\n        total_exchange_fee += inv_exchange_fee\n\n        # 发票级采购成本\n        er = inv_exchange_rate if inv_exchange_rate > 0 else (exchange_rate if exchange_rate else Decimal(\"7.0\"))\n        inv_purchase_cny = inv_amount * er\n\n        # 销售分配比例\n        proportion = Decimal(\"1\")\n        if batch_total_weight > 0 and len(bi_rows) > 1:\n            proportion = inv_weight / batch_total_weight\n\n        # 分配销售\n        inv_sales_net = Decimal(\"0\")\n        inv_sales_weight = Decimal(\"0\")\n        for sale in sales_list:\n            inv_sales_net += _to_decimal(sale.net_amount) * proportion\n            inv_sales_weight += _to_decimal(sale.weight_kg) * proportion\n\n        # 发票级支出\n        inv_expenses = inv_duty + inv_vat + inv_clearance + inv_exchange_payment + inv_exchange_fee\n\n        # 损耗\n        inv_shrinkage = Decimal(\"0\")\n        if inv_weight > 0 and inv_sales_weight > 0:\n            diff = inv_weight - inv_sales_weight\n            if diff > 0:\n                unit_price_usd = inv_amount / inv_weight if inv_weight > 0 else Decimal(\"0\")\n                inv_shrinkage = diff * unit_price_usd * er\n                inv_shrinkage = round(inv_shrinkage, 2)\n\n        # 净利润\n        inv_net_profit = inv_sales_net - inv_expenses - inv_shrinkage\n\n        # 溯源信息\n        pp = await db.execute(select(Company).where(Company.id == inv.processing_plant_id))\n        pp_company = pp.scalar_one_or_none()\n        ff = await db.execute(select(Company).where(Company.id == inv.fish_farm_id))\n        ff_company = ff.scalar_one_or_none()\n\n        # 组装产品明细\n        product_items = [\n            {\n                \"product_name\": p.product_name,\n                \"product_spec\": p.product_spec,\n                \"box_count\": p.box_count or 0,\n                \"net_weight_kg\": round(_to_decimal(p.net_weight_kg), 3),\n                \"unit_price\": round(_to_decimal(p.unit_price), 4),\n                \"total_amount\": round(_to_decimal(p.total_amount), 2),\n            }\n            for p in prods\n        ]\n\n        invoice_details.append({\n            \"invoice_id\": inv.id,\n            \"invoice_no\": inv.invoice_no,\n            \"invoice_date\": inv.invoice_date,\n            \"processing_plant_name\": await _get_company_name(db, inv.processing_plant_id),\n            \"processing_plant_eu_code\": pp_company.code if pp_company else None,\n            \"processing_plant_customs_code\": pp_company.registration_code if pp_company else None,\n            \"processing_plant_coc_no\": pp_company.coc_cert_no if pp_company else None,\n            \"fish_farm_name\": await _get_company_name(db, inv.fish_farm_id),\n            \"fish_farm_ggn\": ff_company.registration_code if ff_company else None,\n            \"fish_farm_coc_no\": ff_company.coc_cert_no if ff_company else None,\n            \"fish_farm_area\": ff_company.farming_area if ff_company else None,\n            \"exporter_name\": await _get_company_name(db, inv.exporter_id),\n            \"total_amount_usd\": round(inv_amount, 2),\n            \"total_boxes\": inv_boxes,\n            \"total_weight_kg\": round(inv_weight, 3),\n            \"purchase_cost_cny\": round(inv_purchase_cny, 2),\n            \"import_duty\": inv_duty,\n            \"import_vat\": inv_vat,\n            \"clearance_cost\": round(inv_clearance, 2),\n            \"exchange_payment\": round(inv_exchange_payment, 2),\n            \"exchange_fee\": round(inv_exchange_fee, 2),\n            \"sales_net\": round(inv_sales_net, 2),\n            \"sales_weight\": round(inv_sales_weight, 3),\n            \"shrinkage\": inv_shrinkage,\n            \"net_profit\": round(inv_net_profit, 2),\n            \"products\": product_items,\n        })\n\n    # 默认汇率\n    if exchange_rate is None or exchange_rate == 0:\n        exchange_rate = Decimal(\"7.0\")\n\n    # 采购成本(CNY)\n    total_purchase_cny = total_purchase_usd * exchange_rate\n\n    # 销售汇总\n    total_sales_amount = Decimal(\"0\")\n    total_sales_net = Decimal(\"0\")\n    total_sales_weight = Decimal(\"0\")\n    total_scan_fee = Decimal(\"0\")\n    total_rounding = Decimal(\"0\")\n    total_commission = Decimal(\"0\")\n    total_after_sales = Decimal(\"0\")\n    total_discount = Decimal(\"0\")\n    sales_count = 0\n\n    sales_data = []\n\n    # 从 CommissionRecord 表查询提成汇总\n    if sales_list:\n        sale_ids = [s.id for s in sales_list]\n        commission_result = await db.execute(\n            select(func.sum(CommissionRecord.commission_amount)).where(CommissionRecord.sale_id.in_(sale_ids))\n        )\n        total_commission = _to_decimal(commission_result.scalar())\n\n    for sale in sales_list:\n        customer_name = await _get_company_name(db, sale.customer_id)\n        total_sales_amount += _to_decimal(sale.gross_amount)\n        total_sales_net += _to_decimal(sale.net_amount)\n        total_sales_weight += _to_decimal(sale.weight_kg)\n        total_scan_fee += _to_decimal(sale.scan_fee)\n        total_rounding += _to_decimal(sale.rounding_adjustment)\n        total_after_sales += _to_decimal(sale.after_sales_adjustment)\n        total_discount += _to_decimal(sale.discount)\n        sales_count += 1\n\n        sales_data.append({\n            \"sale_date\": sale.sale_date,\n            \"customer_name\": customer_name,\n            \"spec\": sale.spec,\n            \"box_count\": sale.box_count,\n            \"weight_kg\": _to_decimal(sale.weight_kg),\n            \"unit_price\": _to_decimal(sale.unit_price),\n            \"gross_amount\": _to_decimal(sale.gross_amount),\n            \"scan_fee\": _to_decimal(sale.scan_fee),\n            \"rounding_adjustment\": _to_decimal(sale.rounding_adjustment),\n            \"commission\": _to_decimal(sale.commission),\n            \"after_sales_adjustment\": _to_decimal(sale.after_sales_adjustment),\n            \"discount\": _to_decimal(sale.discount),\n            \"net_amount\": _to_decimal(sale.net_amount),\n        })\n\n    # 重新计算销售净额（不包含 commission）\n    total_sales_net = (\n        total_sales_amount\n        - total_scan_fee\n        - total_rounding\n        - total_after_sales\n        - total_discount\n    )\n\n    # 其他支出（通过交易流水关联到该批次发票的额外支出）\n    other_expenses_data = []\n    total_other_expenses = Decimal(\"0\")\n    total_clearance_extra = Decimal(\"0\")  # 清关费额外支出（category == \"clearance_payment\"）\n    clearance_extra_items = []\n    if all_inv_ids:\n        other_exp_result = await db.execute(\n            select(TransactionRecord).where(\n                TransactionRecord.type == \"expense\",\n                TransactionRecord.related_invoice_id.in_(all_inv_ids),\n            ).order_by(TransactionRecord.transaction_date.desc())\n        )\n        for txn in other_exp_result.scalars().all():\n            if txn.category == \"clearance_payment\":\n                total_clearance_extra += _to_decimal(txn.amount)\n                clearance_extra_items.append({\n                    \"id\": txn.id,\n                    \"date\": str(txn.transaction_date) if txn.transaction_date else None,\n                    \"amount\": round(_to_decimal(txn.amount), 2),\n                    \"counterparty_name\": txn.counterparty_name,\n                    \"description\": txn.description,\n                    \"reference_no\": txn.reference_no,\n                    \"category\": txn.category,\n                })\n            else:\n                total_other_expenses += _to_decimal(txn.amount)\n                other_expenses_data.append({\n                    \"id\": txn.id,\n                    \"date\": str(txn.transaction_date) if txn.transaction_date else None,\n                    \"amount\": round(_to_decimal(txn.amount), 2),\n                    \"counterparty_name\": txn.counterparty_name,\n                    \"description\": txn.description,\n                    \"reference_no\": txn.reference_no,\n                    \"category\": txn.category,\n                })\n\n    # 清关费合计 = 报关行清关费 + 额外清关支出\n    total_clearance += total_clearance_extra\n\n    # 支出合计\n    total_taxes = total_import_duty + total_import_vat\n    total_expenses = total_taxes + total_clearance + total_exchange_payment + total_exchange_fee + total_other_expenses\n\n    # 损耗\n    shrinkage = Decimal(\"0\")\n    if total_weight > 0 and total_sales_weight > 0:\n        diff = total_weight - total_sales_weight\n        if diff > 0:\n            unit_price_usd = total_purchase_usd / total_weight if total_weight > 0 else Decimal(\"0\")\n            shrinkage = diff * unit_price_usd * exchange_rate\n            shrinkage = round(shrinkage, 2)\n\n    # 净利润 = (销售净额 - 业务员提成) - 支出合计 - 账面损耗\n    net_profit = (total_sales_net - total_commission) - total_expenses - shrinkage\n\n    # 利润率\n    profit_margin = None\n    if total_purchase_cny > 0:\n        profit_margin = round(net_profit / total_purchase_cny * 100, 2)\n\n    return {\n        \"bi_rows\": bi_rows,\n        \"sales_list\": sales_list,\n        \"all_inv_ids\": all_inv_ids,\n        \"invoice_nos\": invoice_nos,\n        \"invoice_details\": invoice_details,\n        \"sales_data\": sales_data,\n        \"other_expenses_data\": other_expenses_data,\n        \"clearance_extra_items\": clearance_extra_items,\n        \"total_purchase_usd\": total_purchase_usd,\n        \"total_purchase_cny\": total_purchase_cny,\n        \"total_weight\": total_weight,\n        \"total_boxes\": total_boxes,\n        \"total_import_duty\": total_import_duty,\n        \"total_import_vat\": total_import_vat,\n        \"total_taxes\": total_taxes,\n        \"total_clearance\": total_clearance,\n        \"clearance_breakdown\": clearance_breakdown,\n        \"exchange_rate\": exchange_rate,\n        \"total_exchange_payment\": total_exchange_payment,\n        \"total_exchange_fee\": total_exchange_fee,\n        \"total_sales_amount\": total_sales_amount,\n        \"total_sales_net\": total_sales_net,\n        \"total_sales_weight\": total_sales_weight,\n        \"total_scan_fee\": total_scan_fee,\n        \"total_rounding\": total_rounding,\n        \"total_commission\": total_commission,\n        \"total_after_sales\": total_after_sales,\n        \"total_discount\": total_discount,\n        \"sales_count\": sales_count,\n        \"total_other_expenses\": total_other_expenses,\n        \"total_clearance_extra\": total_clearance_extra,\n        \"total_expenses\": total_expenses,\n        \"shrinkage\": shrinkage,\n        \"net_profit\": net_profit,\n        \"profit_margin\": profit_margin,\n        \"is_exchange_estimated\": is_exchange_estimated,\n    }\n\n""".splitlines(keepends=True)

# ------------------------------------------------------------------
# Locate key line numbers (1-based)
# ------------------------------------------------------------------

def find_line(pattern, start=0):
    for i in range(start, len(lines)):
        if pattern in lines[i]:
            return i
    raise ValueError(f"Pattern not found: {pattern!r}")

# list_batch_reports cumulative profit section
lb_start = find_line("    cumulative_profit_map = {}", 0)           # ~517 0-based
lb_end   = find_line("    items: List[BatchReportSummaryItem] = []", lb_start)  # ~670

# get_batch_report function
gb_start = find_line("@router.get(\"/batch/{batch_id}\"", 0)          # ~941
gb_core_start = find_line("    # 获取关联发票\n", gb_start)            # ~953
gb_cumulative_start = find_line("    # 累计利润（按日期顺序累加到当前批次为止的已完成批次净利润之和）\n", gb_core_start)  # ~1345

# Verify we found the right cumulative profit line (should be inside get_batch_report)
# There's another cumulative profit line at line 518 but we already passed it.

print(f"list_batch_reports cumulative: lines {lb_start+1}-{lb_end}")
print(f"get_batch_report core: lines {gb_core_start+1}-{gb_cumulative_start}")

# ------------------------------------------------------------------
# 1. Replace list_batch_reports cumulative profit pre-calculation
# ------------------------------------------------------------------

NEW_LB_BLOCK = """    # 预计算所有已完成批次的累计利润
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
        cb_batch = await db.get(Batch, cb_id)
        if cb_batch:
            cb_data = await _calc_batch_financials(db, cb_batch)
            if cb_data:
                cumulative_profit_map[cb_id] = round(running_cumulative, 2)
                running_cumulative += cb_data["net_profit"]

""".splitlines(keepends=True)

# Replace lines lb_start .. lb_end-1 with NEW_LB_BLOCK
lines = lines[:lb_start] + NEW_LB_BLOCK + lines[lb_end:]

# Adjust line numbers after replacement
shift = len(NEW_LB_BLOCK) - (lb_end - lb_start)
gb_start += shift
gb_core_start += shift
gb_cumulative_start += shift

print(f"After LB replacement, shift={shift}")
print(f"get_batch_report core now: lines {gb_core_start+1}-{gb_cumulative_start}")

# ------------------------------------------------------------------
# 2. Insert helper before get_batch_report
# ------------------------------------------------------------------

insert_pos = gb_start  # before @router.get("/batch/{batch_id}")
lines = lines[:insert_pos] + HELPER_LINES + lines[insert_pos:]
shift2 = len(HELPER_LINES)
gb_core_start += shift2
gb_cumulative_start += shift2

print(f"After helper insertion, shift2={shift2}")
print(f"get_batch_report core now: lines {gb_core_start+1}-{gb_cumulative_start}")

# ------------------------------------------------------------------
# 3. Replace get_batch_report core calculation with helper call
# ------------------------------------------------------------------

NEW_GB_CORE = """    data = await _calc_batch_financials(db, batch)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次没有关联发票")

    # Unpack for response assembly
    all_inv_ids = data["all_inv_ids"]
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
    sales_count = data["sales_count"]
    total_other_expenses = data["total_other_expenses"]
    total_clearance_extra = data["total_clearance_extra"]
    total_expenses = data["total_expenses"]
    shrinkage = data["shrinkage"]
    net_profit = data["net_profit"]
    profit_margin = data["profit_margin"]
    is_exchange_estimated = data["is_exchange_estimated"]

""".splitlines(keepends=True)

lines = lines[:gb_core_start] + NEW_GB_CORE + lines[gb_cumulative_start:]

# ------------------------------------------------------------------
# 4. Update return statement in get_batch_report to use unpacked data
# ------------------------------------------------------------------

# Find the return statement inside get_batch_report
gb_return_start = find_line("    return BatchReportDetail(", gb_core_start)
gb_return_end = find_line("    )\n", gb_return_start)

# We need to update references inside the return block:
# invoice_details -> [BatchReportInvoiceDetail(**d) for d in invoice_details_raw]
# len(invoice_details) -> len(invoice_details_raw)
# other references already match unpacked variable names

return_block = lines[gb_return_start:gb_return_end+1]
return_text = "".join(return_block)

# Replace invoice_details references
return_text = return_text.replace(
    "invoice_count=len(invoice_details),",
    "invoice_count=len(invoice_details_raw),"
)
return_text = return_text.replace(
    "invoices=invoice_details,",
    "invoices=[BatchReportInvoiceDetail(**d) for d in invoice_details_raw],"
)

lines = lines[:gb_return_start] + [return_text] + lines[gb_return_end+1:]

# ------------------------------------------------------------------
# 5. Write back
# ------------------------------------------------------------------

with open(FILE, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Done. Refactoring complete.")
