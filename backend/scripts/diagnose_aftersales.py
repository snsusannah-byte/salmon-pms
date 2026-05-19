#!/usr/bin/env python3
"""
诊断 after_sales_adjustment 残留问题
直接连接到你的数据库运行
"""
import sqlite3
from decimal import Decimal

def diagnose_aftersales(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"数据库: {db_path}")
    print("=" * 70)
    
    # 1. 查所有整鱼销售
    cursor.execute("""
        SELECT s.*, c.name as customer_name, b.batch_name
        FROM whole_fish_sales s
        LEFT JOIN companies c ON s.customer_id = c.id
        LEFT JOIN batches b ON s.batch_id = b.id
        ORDER BY s.id
    """)
    sales = cursor.fetchall()
    
    print(f"\n【整鱼销售】共 {len(sales)} 条")
    
    problematic = []
    for sale in sales:
        sid = sale['id']
        gross = Decimal(str(sale['gross_amount'] or 0))
        scan = Decimal(str(sale['scan_fee'] or 0))
        rounding = Decimal(str(sale['rounding_adjustment'] or 0))
        after = Decimal(str(sale['after_sales_adjustment'] or 0))
        discount = Decimal(str(sale['discount'] or 0))
        commission = Decimal(str(sale['commission'] or 0))
        net = Decimal(str(sale['net_amount'] or 0))
        paid = Decimal(str(sale['paid_amount'] or 0))
        status = sale['status']
        
        # 检查售后记录
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
        
        expected_after = actual_aftersales + return_amount
        expected_net = gross - scan - rounding - expected_after - discount - commission
        expected_net = max(Decimal("0"), expected_net)
        
        # 判定正确状态
        if paid >= expected_net and expected_net > 0:
            expected_status = "fully_paid"
        elif paid > 0:
            expected_status = "partial_paid"
        else:
            expected_status = "pending"
        
        # 检测问题
        issues = []
        if after != expected_after:
            issues.append(f"after_sales_adjustment: 实际={after} 应有={expected_after}")
        if net != expected_net:
            issues.append(f"net_amount: 实际={net} 应有={expected_net}")
        if status != expected_status:
            issues.append(f"status: 实际={status} 应有={expected_status}")
        
        if issues:
            problematic.append({
                'id': sid,
                'sale_no': sale.get('sale_no') or f"#{sid}",
                'customer': sale['customer_name'] or 'N/A',
                'gross': float(gross),
                'after': float(after),
                'expected_after': float(expected_after),
                'net': float(net),
                'expected_net': float(expected_net),
                'paid': float(paid),
                'status': status,
                'expected_status': expected_status,
                'issues': issues
            })
            print(f"\n  ⚠️ 销售单 {sale.get('sale_no') or f'#{sid}'} | 客户: {sale['customer_name'] or 'N/A'}")
            for issue in issues:
                print(f"     - {issue}")
    
    if not problematic:
        print("\n✅ 所有整鱼销售记录数据一致，无残留问题")
    else:
        print(f"\n\n{'='*70}")
        print(f"发现 {len(problematic)} 条问题记录")
        print(f"{'='*70}")
        print("\n📋 需补录退货单的记录（售后已删但金额未恢复）:")
        for p in problematic:
            if p['expected_after'] == 0 and p['after'] > 0:
                print(f"  - {p['sale_no']} | 差额: ¥{p['expected_net'] - p['paid']:.2f} | 应补录退货单")
    
    conn.close()
    return problematic


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "salmon_pms_dev.db"
    diagnose_aftersales(db_path)
