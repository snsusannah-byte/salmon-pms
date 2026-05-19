#!/usr/bin/env python3
"""
销售单付款状态修复脚本
用途：
  1. 重新计算所有销售单的 paid_amount（基于 sales_receipts 合计）
  2. 重新计算 after_sales_adjustment（基于存在的售后记录 + 退货单）
  3. 重新计算 net_amount
  4. 根据 paid vs net 重新确定正确状态
  5. 修正不一致的数据

运行方式：
  cd /path/to/backend && python3 scripts/fix_sales_status.py [--dry-run]
"""

import sqlite3
import sys
from decimal import Decimal
from datetime import datetime


def fix_sales_status(db_path: str, dry_run: bool = True):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    changes_log = []

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

        # 1.2 计算实际售后调整（aftersales_records + return_orders）
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM aftersales_records WHERE sale_id = ?",
            (sale_id,)
        )
        aftersales_amount = Decimal(str(cursor.fetchone()[0] or 0))

        # 检查 return_orders 表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='return_orders'"
        )
        return_orders_exists = cursor.fetchone() is not None

        return_amount = Decimal("0")
        if return_orders_exists:
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0) FROM return_orders
                WHERE whole_fish_sale_id = ? AND status NOT IN ('cancelled', 'rejected')
            """, (sale_id,))
            return_amount = Decimal(str(cursor.fetchone()[0] or 0))

        actual_aftersales = aftersales_amount + return_amount

        # ⚠️ 关键修复：如果售后记录已删除，但 after_sales_adjustment 还残留值，清零它
        orphaned_aftersales = False
        if old_aftersales > 0 and aftersales_amount == 0 and return_amount == 0:
            orphaned_aftersales = True
            issues.append(f"售后记录已删，after_sales_adjustment 残留: {old_aftersales} → 0")

        # 1.3 重新计算净金额
        new_net = gross - scan_fee - rounding - actual_aftersales - discount - commission
        new_net = max(Decimal("0"), new_net)  # 不能为负

        # 1.4 确定正确状态
        if actual_paid >= new_net and new_net > 0:
            new_status = "fully_paid"
        elif actual_paid > 0:
            new_status = "partial_paid"
        else:
            new_status = "pending"

        # 如果有进行中的退货，标记为售后中
        if return_orders_exists:
            cursor.execute("""
                SELECT COUNT(*) FROM return_orders
                WHERE whole_fish_sale_id = ?
                AND status IN ('draft', 'pending_approval', 'approved', 'refunding')
            """, (sale_id,))
            in_progress_returns = cursor.fetchone()[0]
            if in_progress_returns > 0:
                new_status = "after_sales"

        # 1.5 检查是否需要修复
        issues = []
        if actual_paid != old_paid:
            issues.append(f"paid: {old_paid} → {actual_paid}")
        if actual_aftersales != old_aftersales:
            issues.append(f"aftersales: {old_aftersales} → {actual_aftersales}")
        if new_net != old_net:
            issues.append(f"net: {old_net} → {new_net}")
        if new_status != old_status:
            issues.append(f"status: {old_status} → {new_status}")

        if issues:
            log(f"\n  📋 销售单 #{sale_id} | {sale['sale_no'] or 'N/A'} | 客户: {sale['customer_name'] or 'N/A'}")
            log(f"     金额: 毛{gross} - 扫{scan_fee} - 抹{rounding} - 售后{actual_aftersales} - 折{discount} - 提{commission} = 净{new_net}")
            log(f"     已付: {actual_paid} | 差额: {new_net - actual_paid}")
            for issue in issues:
                log(f"     ⚠️ {issue}")

            if not dry_run:
                cursor.execute("""
                    UPDATE whole_fish_sales
                    SET paid_amount = ?, after_sales_adjustment = ?, net_amount = ?, status = ?, updated_at = ?
                    WHERE id = ?
                """, (float(actual_paid), float(actual_aftersales), float(new_net), new_status, datetime.now(), sale_id))
                log(f"     ✅ 已修复")
        else:
            # 数据正常，静默跳过（可选：打印通过记录）
            pass

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
        old_aftersales = Decimal(str(sale.get('after_sales_adjustment') or 0))
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

        # 2.2 实际售后（finished_product_aftersales + return_orders）
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

        # 2.3 重新计算净金额
        new_net = gross - scan_fee - actual_aftersales - discount - commission
        new_net = max(Decimal("0"), new_net)

        # 2.4 状态
        if actual_paid >= new_net and new_net > 0:
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
            in_progress_returns = cursor.fetchone()[0]
            if in_progress_returns > 0:
                new_status = "after_sales"

        # 2.5 检查差异
        issues = []
        if actual_paid != old_paid:
            issues.append(f"paid: {old_paid} → {actual_paid}")
        if actual_aftersales != old_aftersales:
            issues.append(f"aftersales: {old_aftersales} → {actual_aftersales}")
        if new_net != old_net:
            issues.append(f"net: {old_net} → {new_net}")
        if new_status != old_status:
            issues.append(f"status: {old_status} → {new_status}")

        if issues:
            log(f"\n  📋 成品销售 #{sale_id} | 客户: {sale['customer_name'] or 'N/A'} | 产品: {sale['product_name'] or 'N/A'}")
            log(f"     金额: 毛{gross} - 扫{scan_fee} - 售后{actual_aftersales} - 折{discount} - 提{commission} = 净{new_net}")
            log(f"     已付: {actual_paid} | 差额: {new_net - actual_paid}")
            for issue in issues:
                log(f"     ⚠️ {issue}")

            if not dry_run:
                cursor.execute("""
                    UPDATE finished_product_sales
                    SET paid_amount = ?, net_amount = ?, status = ?, updated_at = ?
                    WHERE id = ?
                """, (float(actual_paid), float(new_net), new_status, datetime.now(), sale_id))
                # 注意：成品销售表没有 after_sales_adjustment 字段
                log(f"     ✅ 已修复")

    # ============================================================
    # 3. 汇总 & 提交
    # ============================================================
    log(f"\n{'='*70}")
    if dry_run:
        log("【预览模式】以上是需要修复的记录")
        log("运行时不加 --dry-run 参数将实际写入数据库")
    else:
        conn.commit()
        log("【修复完成】已提交到数据库")

    log(f"{'='*70}")
    conn.close()

    # 保存日志
    with open("fix_sales_status.log", "w", encoding="utf-8") as f:
        f.write("\n".join(changes_log))
    print(f"\n日志已保存到 fix_sales_status.log")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    db_path = "salmon_pms_dev.db"

    # 支持自定义数据库路径
    for arg in sys.argv[1:]:
        if arg.endswith(".db"):
            db_path = arg
            break

    print(f"数据库: {db_path}")
    print(f"模式: {'预览 (dry-run)' if dry_run else '实际修复'}")
    print(f"运行: python3 scripts/fix_sales_status.py {' '.join(sys.argv[1:])}")

    fix_sales_status(db_path, dry_run=dry_run)
