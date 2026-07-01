"""
验证销售单 net_amount 一致性
检查 sale.net_amount 是否等于 gross - scan - rounding - after_sales - discount - commission
"""
import asyncio
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 数据库连接（从 .env 读取）
DATABASE_URL = "postgresql+asyncpg://salmon:001978@localhost:5432/salmon_pms"

async def check_sales_consistency():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # 查询所有不一致的销售记录
        result = await conn.execute(text("""
            SELECT 
                id, sale_no, gross_amount, scan_fee, rounding_adjustment,
                after_sales_adjustment, discount, commission, net_amount,
                gross_amount - COALESCE(scan_fee, 0) - COALESCE(rounding_adjustment, 0) 
                - COALESCE(after_sales_adjustment, 0) - COALESCE(discount, 0) 
                - COALESCE(commission, 0) AS expected_net
            FROM whole_fish_sales
            WHERE net_amount IS NOT NULL
            ORDER BY ABS(
                net_amount - (
                    gross_amount - COALESCE(scan_fee, 0) - COALESCE(rounding_adjustment, 0) 
                    - COALESCE(after_sales_adjustment, 0) - COALESCE(discount, 0) 
                    - COALESCE(commission, 0)
                )
            ) DESC
        """))
        
        rows = result.all()
        if not rows:
            print("✅ 所有销售单 net_amount 一致")
            return
        
        print(f"⚠️ 发现 {len(rows)} 条不一致的销售单：\n")
        print(f"{'ID':<5} {'销售单号':<20} {'数据库net':<12} {'计算值':<12} {'差异':<10} {'commission':<12}")
        print("-" * 80)
        
        total_diff = Decimal("0")
        for row in rows:
            id_, sale_no, gross, scan, rounding, after_sales, discount, commission, net, expected, diff = row
            total_diff += diff
            print(f"{id_:<5} {sale_no or '':<20} {float(net):<12.2f} {float(expected):<12.2f} {float(diff):<10.2f} {float(commission or 0):<12.2f}")
        
        print("-" * 80)
        print(f"总差异: {float(total_diff):.2f}")
        
        # 检查 commission 字段 vs CommissionRecord 表
        print("\n\n🔍 检查 commission 字段与 CommissionRecord 表差异：")
        result2 = await conn.execute(text("""
            SELECT 
                w.id, w.sale_no, w.commission,
                COALESCE(c.total_commission, 0) AS record_commission,
                w.commission - COALESCE(c.total_commission, 0) AS commission_diff
            FROM whole_fish_sales w
            LEFT JOIN (
                SELECT sale_id, SUM(commission_amount) AS total_commission
                FROM commission_records
                GROUP BY sale_id
            ) c ON w.id = c.sale_id
            WHERE ABS(COALESCE(w.commission, 0) - COALESCE(c.total_commission, 0)) > 0.01
            ORDER BY ABS(commission_diff) DESC
        """))
        
        rows2 = result2.all()
        if rows2:
            print(f"发现 {len(rows2)} 条 commission 不一致：")
            for row in rows2:
                id_, sale_no, field_comm, record_comm, diff = row
                print(f"  ID={id_} {sale_no}: 字段={float(field_comm or 0):.2f}, 记录={float(record_comm):.2f}, 差异={float(diff):.2f}")
        else:
            print("✅ commission 字段与 CommissionRecord 表一致")

if __name__ == "__main__":
    asyncio.run(check_sales_consistency())
