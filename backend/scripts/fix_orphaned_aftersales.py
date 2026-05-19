#!/usr/bin/env python3
"""
销售单售后数据修复 + 补录清单生成
================================

用途：
  1. 修复被删除售后记录后残留的数据问题
  2. 重新计算付款状态和净金额
  3. 生成"需补录退货单"的清单

适用场景：
  用户删除了旧版"售后调整"记录，但销售单上的 after_sales_adjustment 
  字段值还在，导致净金额虚低、付款状态错误（显示"全部收款"实际是"部分付款"）

修复逻辑：
  - 遍历所有销售单
  - 检查 after_sales_adjustment > 0 但无售后记录的情况
  - 清零 after_sales_adjustment，恢复净金额
  - 重新计算付款状态

运行方式：
  cd /path/to/backend
  
  # 第一步：预览
  python3 scripts/fix_orphaned_aftersales.py --dry-run
  
  # 第二步：执行修复
  python3 scripts/fix_orphaned_aftersales.py
  
  # 第三步：查看补录清单（执行后会生成 orphaned_aftersales_report.md）
  cat orphaned_aftersales_report.md
"""

import sqlite3
import sys
from decimal import Decimal
from datetime import datetime


def fix_orphaned_aftersales(db_path: str, dry_run: bool = True):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    changes_log = []
    orphaned_records = []  # 需要补录退货单的记录

    def log(msg):
        print(msg)
        changes_log.append(msg)

    # ============================================================
    # 1. 整鱼销售
    # ============================================================
    cursor.execute("""
        SELECT s.*, c.name as customer_name
        FROM whole_fish_sales s
        LEFT JOIN companies c ON s.customer_id = c.id
        ORDER BY s.id
    """)
    whole_fish_sales = cursor.fetchall()

    log(f"\n{'='*70}")
    log(f"【整鱼销售检查】共 {len(whole_fish_sales)} 条")
    log(f"{'='*70}")

    for sale in whole_fish_sales:
        sale_id = sale['id']
        gross = Decimal(str(sale['gross_amount'] or 0))
        scan_fee = Decimal(str(sale['scan_fee'] or 0))
        rounding = Decimal(str(sale['rounding_adjustment'] or 0))
        old_aftersales = Decimal(str(sale['after_sales_adjustment'] or 0))
        discount = Decimal(str(sale['discount'] or 0))
        commission = Decimal(str(sale['commission'] or 0))
        old_net = Decimal(str(sale['net_amount'] or 0))
        old_paid = Decimal(str(sale['paid_amount'] or 0))
        old_status = sale['status']

        # 1.1 计算实际收款合计
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM sales_receipts WHERE sale_id = ?",
            (sale_id,)
        )
        actual_paid = Decimal(str(cursor.fetchone()[0] or 0))

        # 1.2 计算实际售后（aftersales_records + return_orders）
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM aftersales_records WHERE sale_id = ?",
            (sale_id,)
        )
        aftersales_amount = Decimal(str(cursor.fetchone()[0] or 0))

        return_orders_exists = False
        return_amount = Decimal("0")
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='return_orders'"
        )
        if cursor.fetchone():
            return_orders_exists = True
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0) FROM return_orders
                WHERE whole_fish_sale_id = ? AND status NOT IN ('cancelled', 'rejected')
            """, (sale_id,))
            return_amount = Decimal(str(cursor.fetchone()[0] or 0))

        actual_aftersales = aftersales_amount + return_amount

        # ⚠️ 关键检测：售后记录已删除，但字段值还在
        needs_fix = False
        issues = []
        is_orphaned = False

        if old_aftersales > 0 and aftersales_amount == 0 and return_amount == 0:
            # 售后调整字段有值，但无任何售后/退货记录 → 残留数据
            is_orphaned = True
            actual_aftersales = Decimal("0")
            issues.append(f"⚠️ 售后记录已删，残留 after_sales_adjustment={old_aftersales}，清零")
            needs_fix = True

        # 1.3 重新计算净金额
        new_net = gross - scan_fee - rounding - actual_aftersales - discount - commission
        new_net = max(Decimal("0"), new_net)

        # 1.4 状态判定
        if actual_paid >= new_net and new_net > 0:
            new_status = "fully_paid"
        elif actual_paid > 0:
            new_status = "partial_paid"
        else:
            new_status = "pending"

        # 如果有进行中的退货
        if return_orders_exists:
            cursor.execute("""
                SELECT COUNT(*) FROM return_orders
                WHERE whole_fish_sale_id = ?
                AND status IN ('draft', 'pending_approval', 'approved', 'refunding')
            """, (sale_id,))
            if cursor.fetchone()[0] > 0:
                new_status = "after_sales"

        # 检查其他差异
        if actual_paid != old_paid:
            issues.append(f"paid_amount: {old_paid} → {actual_paid}")
            needs_fix = True
        if new_net != old_net:
            issues.append(f"net_amount: {old_net} → {new_net}")
            needs_fix = True
        if new_status != old_status:
            issues.append(f"status: {old_status} → {new_status}")
            needs_fix = True

        if needs_fix:
            log(f"\n  📋 销售单 #{sale_id} | {sale['sale_no'] or 'N/A'} | 客户: {sale['customer_name'] or 'N/A'}")
            log(f"     毛金额: ¥{gross:,.2f} | 扫码: ¥{scan_fee:,.2f} | 抹零: ¥{rounding:,.2f}")
            log(f"     售后: ¥{old_aftersales:,.2f}→¥{actual_aftersales:,.2f} | 折扣: ¥{discount:,.2f} | 提成: ¥{commission:,.2f}")
            log(f"     净金额: ¥{old_net:,.2f} → ¥{new_net:,.2f} | 已付: ¥{actual_paid:,.2f}")
            log(f"     差额: ¥{new_net - actual_paid:,.2f} | 状态: {old_status} → {new_status}")
            for issue in issues:
                log(f"     {issue}")

            if not dry_run:
                cursor.execute("""
                    UPDATE whole_fish_sales
                    SET paid_amount = ?, after_sales_adjustment = ?, net_amount = ?, status = ?, updated_at = ?
                    WHERE id = ?
                """, (float(actual_paid), float(actual_aftersales), float(new_net), new_status, datetime.now(), sale_id))
                log(f"     ✅ 已修复")

            if is_orphaned and new_net > actual_paid:
                # 差额需要补录退货单
                orphaned_records.append({
                    "sale_type": "whole_fish",
                    "sale_id": sale_id,
                    "sale_no": sale['sale_no'] or f"#{sale_id}",
                    "customer_name": sale['customer_name'] or 'N/A',
                    "sale_date": sale['sale_date'],
                    "gross_amount": float(gross),
                    "old_aftersales": float(old_aftersales),
                    "new_net": float(new_net),
                    "paid": float(actual_paid),
                    "diff": float(new_net - actual_paid),
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": "售后调整记录已删除，需补录退货单",
                })

    # ============================================================
    # 2. 成品销售
    # ============================================================
    cursor.execute("""
        SELECT s.*, c.name as customer_name, p.name as product_name
        FROM finished_product_sales s
        LEFT JOIN companies c ON s.customer_id = c.id
        LEFT JOIN products p ON s.product_id = p.id
        ORDER BY s.id
    """)
    fp_sales = cursor.fetchall()

    log(f"\n{'='*70}")
    log(f"【成品销售检查】共 {len(fp_sales)} 条")
    log(f"{'='*70}")

    for sale in fp_sales:
        sale_id = sale['id']
        gross = Decimal(str(sale['gross_amount'] or 0))
        scan_fee = Decimal(str(sale['scan_fee'] or 0))
        # 成品表没有 after_sales_adjustment 字段，用旧售后记录计算
        discount = Decimal(str(sale['discount'] or 0))
        commission = Decimal(str(sale['commission'] or 0))
        old_net = Decimal(str(sale['net_amount'] or 0))
        old_paid = Decimal(str(sale['paid_amount'] or 0))
        old_status = sale['status']

        # 2.1 实际收款
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM sales_receipts WHERE sale_id = ?",
            (sale_id,)
        )
        actual_paid = Decimal(str(cursor.fetchone()[0] or 0))

        # 2.2 实际售后
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM finished_product_aftersales WHERE sale_id = ?",
            (sale_id,)
        )
        aftersales_amount = Decimal(str(cursor.fetchone()[0] or 0))

        return_amount = Decimal("0")
        if return_orders_exists:
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0) FROM return_orders
                WHERE finished_product_sale_id = ? AND status NOT IN ('cancelled', 'rejected')
            """, (sale_id,))
            return_amount = Decimal(str(cursor.fetchone()[0] or 0))

        actual_aftersales = aftersales_amount + return_amount

        # 成品表没有 after_sales_adjustment 字段，用 net_amount 反推
        # 如果 net < gross 但无售后记录，可能是历史残留
        # 这里只修复 paid_amount 和 status
        needs_fix = False
        issues = []
        is_orphaned = False

        # 2.3 重新计算净金额（成品表没有 after_sales_adjustment）
        # 如果有旧售后记录，net_amount 应该是 gross - aftersales
        # 如果没有售后记录但 net < gross，可能是旧数据残留
        expected_net = gross - scan_fee - actual_aftersales - discount - commission
        expected_net = max(Decimal("0"), expected_net)

        if expected_net != old_net and actual_aftersales == 0:
            is_orphaned = True
            issues.append(f"⚠️ 净金额异常: {old_net} → {expected_net} (无售后记录)")
            needs_fix = True

        # 2.4 状态
        if actual_paid >= expected_net and expected_net > 0:
            new_status = "fully_paid"
        elif actual_paid > 0:
            new_status = "partial_paid"
        else:
            new_status = "pending"

        if return_orders_exists:
            cursor.execute("""
                SELECT COUNT(*) FROM return_orders
                WHERE finished_product_sale_id = ?
                AND status IN ('draft', 'pending_approval', 'approved', 'refunding')
            """, (sale_id,))
            if cursor.fetchone()[0] > 0:
                new_status = "after_sales"

        if actual_paid != old_paid:
            issues.append(f"paid_amount: {old_paid} → {actual_paid}")
            needs_fix = True
        if new_status != old_status:
            issues.append(f"status: {old_status} → {new_status}")
            needs_fix = True

        if needs_fix:
            log(f"\n  📋 成品销售 #{sale_id} | 客户: {sale['customer_name'] or 'N/A'} | 产品: {sale['product_name'] or 'N/A'}")
            log(f"     毛金额: ¥{gross:,.2f} | 净金额: ¥{old_net:,.2f} → ¥{expected_net:,.2f} | 已付: ¥{actual_paid:,.2f}")
            log(f"     差额: ¥{expected_net - actual_paid:,.2f} | 状态: {old_status} → {new_status}")
            for issue in issues:
                log(f"     {issue}")

            if not dry_run:
                cursor.execute("""
                    UPDATE finished_product_sales
                    SET paid_amount = ?, net_amount = ?, status = ?, updated_at = ?
                    WHERE id = ?
                """, (float(actual_paid), float(expected_net), new_status, datetime.now(), sale_id))
                log(f"     ✅ 已修复")

            if is_orphaned and expected_net > actual_paid:
                orphaned_records.append({
                    "sale_type": "finished_product",
                    "sale_id": sale_id,
                    "sale_no": f"#{sale_id}",
                    "customer_name": sale['customer_name'] or 'N/A',
                    "sale_date": sale['sale_date'],
                    "gross_amount": float(gross),
                    "old_aftersales": float(gross - old_net),
                    "new_net": float(expected_net),
                    "paid": float(actual_paid),
                    "diff": float(expected_net - actual_paid),
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": "成品净金额异常，可能售后记录已删除",
                })

    # ============================================================
    # 3. 提交 & 生成补录清单
    # ============================================================
    log(f"\n{'='*70}")
    if dry_run:
        log("【预览模式】以上是需要修复的记录")
        log("运行时不加 --dry-run 参数将实际写入数据库")
    else:
        conn.commit()
        log("【修复完成】已提交到数据库")

    # 生成补录清单
    if orphaned_records:
        generate_report(orphaned_records)
        log(f"\n📋 发现 {len(orphaned_records)} 条记录需要补录退货单")
        log(f"   详见 orphaned_aftersales_report.md")
    else:
        log(f"\n✅ 没有需要补录退货单的记录")

    log(f"{'='*70}")
    conn.close()

    # 保存日志
    with open("fix_orphaned_aftersales.log", "w", encoding="utf-8") as f:
        f.write("\n".join(changes_log))
    print(f"\n日志已保存到 fix_orphaned_aftersales.log")


def generate_report(records):
    """生成补录清单报告"""
    lines = [
        "# 需补录退货单的销售记录清单",
        "",
        "> 本清单由 `fix_orphaned_aftersales.py` 自动生成",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 说明",
        "",
        "以下销售单的售后调整记录已被删除，但销售单金额未恢复。",
        "修复后净金额恢复，付款状态变为「部分付款」，需要用新的「售后/退货」功能补录退货单。",
        "",
        "## 补录清单",
        "",
        "| 类型 | 销售单 | 日期 | 客户 | 毛金额 | 需扣售后 | 净金额 | 已付 | 差额 | 操作 |",
        "|------|--------|------|------|--------|----------|--------|------|------|------|",
    ]

    for r in records:
        sale_type_label = "整鱼" if r['sale_type'] == 'whole_fish' else "成品"
        lines.append(
            f"| {sale_type_label} | {r['sale_no']} | {r['sale_date']} | {r['customer_name']} | "
            f"¥{r['gross_amount']:,.2f} | ¥{r['old_aftersales']:,.2f} | "
            f"¥{r['new_net']:,.2f} | ¥{r['paid']:,.2f} | ¥{r['diff']:,.2f} | "
            f"[售后] → 新建退货单 ¥{r['diff']:,.2f} |"
        )

    lines.extend([
        "",
        "## 操作步骤",
        "",
        "1. 打开「整鱼销售」或「成品销售」页面",
        "2. 找到上表中的销售单",
        "3. 点击「售后」按钮（或进入详情页 → 售后标签）",
        "4. 填写退货信息：",
        "   - 退货日期：建议填写原销售日期或实际退货日期",
        "   - 退货金额：填写「差额」列的金额",
        "   - 退货原因：根据实际情况选择（质量问题/物流损坏/规格不符等）",
        "   - 备注：可注明「历史数据补录」",
        "5. 提交退货单",
        "",
        "## 补录后状态",
        "",
        "- 退货单状态设为 `completed`（已完成）",
        "- 销售单状态自动同步为正确的付款状态",
        "- after_sales_adjustment 会自动更新为退货金额",
        "",
    ])

    with open("orphaned_aftersales_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n补录清单已保存到 orphaned_aftersales_report.md")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    db_path = "salmon_pms_dev.db"

    for arg in sys.argv[1:]:
        if arg.endswith(".db"):
            db_path = arg
            break

    print(f"数据库: {db_path}")
    print(f"模式: {'预览 (dry-run)' if dry_run else '实际修复'}")
    print()

    fix_orphaned_aftersales(db_path, dry_run=dry_run)
