#!/usr/bin/env python3
"""
单条销售记录修复 - 针对售后已删但净金额未恢复的问题
用法: python3 fix_single_sale.py [销售单ID或sale_no]
"""

import sqlite3
import sys
from decimal import Decimal
from datetime import datetime

def fix_sale(db_path: str, target_sale: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 尝试用 ID 或 sale_no 查找
    try:
        sale_id = int(target_sale)
        cursor.execute("SELECT * FROM whole_fish_sales WHERE id = ?", (sale_id,))
    except ValueError:
        # 没有 sale_no 字段就用 id
        print(f"⚠️ 数据库没有 sale_no 字段，尝试查找 ID={target_sale}")
        try:
            sale_id = int(target_sale.replace("XS", "").split("-")[0]) if target_sale.startswith("XS") else int(target_sale)
            cursor.execute("SELECT * FROM whole_fish_sales WHERE id = ?", (sale_id,))
        except:
            print(f"❌ 无法解析销售单号: {target_sale}")
            return
    
    sale = cursor.fetchone()
    if not sale:
        print(f"❌ 销售单 {target_sale} 未找到")
        return
    
    sid = sale['id']
    gross = Decimal(str(sale['gross_amount'] or 0))
    scan = Decimal(str(sale['scan_fee'] or 0))
    rounding = Decimal(str(sale['rounding_adjustment'] or 0))
    old_after = Decimal(str(sale['after_sales_adjustment'] or 0))
    discount = Decimal(str(sale['discount'] or 0))
    commission = Decimal(str(sale['commission'] or 0))
    old_net = Decimal(str(sale['net_amount'] or 0))
    paid = Decimal(str(sale['paid_amount'] or 0))
    old_status = sale['status']
    
    print(f"\n{'='*60}")
    print(f"【销售单 #{sid}】修复前")
    print(f"{'='*60}")
    print(f"  销售金额: ¥{gross:,.2f}")
    print(f"  售后调整: ¥{old_after:,.2f}")
    print(f"  净金额:   ¥{old_net:,.2f}")
    print(f"  已付:     ¥{paid:,.2f}")
    print(f"  状态:     {old_status}")
    
    # 检查实际售后记录
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM aftersales_records WHERE sale_id = ?", (sid,))
    actual_aftersales = Decimal(str(cursor.fetchone()[0] or 0))
    
    # 检查退货单
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='return_orders'")
    return_exists = cursor.fetchone()
    return_amount = Decimal("0")
    if return_exists:
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) FROM return_orders
            WHERE whole_fish_sale_id = ? AND status NOT IN ('cancelled', 'rejected')
        """, (sid,))
        return_amount = Decimal(str(cursor.fetchone()[0] or 0))
    
    new_after = actual_aftersales + return_amount
    new_net = gross - scan - rounding - new_after - discount - commission
    new_net = max(Decimal("0"), new_net)
    
    if paid >= new_net and new_net > 0:
        new_status = "fully_paid"
    elif paid > 0:
        new_status = "partial_paid"
    else:
        new_status = "pending"
    
    print(f"\n{'='*60}")
    print(f"【修复后】")
    print(f"{'='*60}")
    print(f"  售后调整: ¥{old_after:,.2f} → ¥{new_after:,.2f}")
    print(f"  净金额:   ¥{old_net:,.2f} → ¥{new_net:,.2f}")
    print(f"  差额:     ¥{new_net - paid:,.2f}")
    print(f"  状态:     {old_status} → {new_status}")
    
    confirm = input("\n确认修复? (y/n): ").strip().lower()
    if confirm == 'y':
        cursor.execute("""
            UPDATE whole_fish_sales
            SET after_sales_adjustment = ?,
                net_amount = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
        """, (float(new_after), float(new_net), new_status, datetime.now(), sid))
        conn.commit()
        print(f"\n✅ 已修复！刷新页面查看")
    else:
        print(f"\n❌ 已取消")
    
    conn.close()

if __name__ == "__main__":
    db_path = "salmon_pms_dev.db"
    target = sys.argv[1] if len(sys.argv) > 1 else "6"
    
    print(f"数据库: {db_path}")
    print(f"目标销售单: {target}")
    
    fix_sale(db_path, target)
