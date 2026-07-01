"""
修复销售单 net_amount 不一致问题
扫描所有 net_amount != gross_amount - scan_fee - rounding - after_sales - discount - commission 的记录
并重新同步
"""
import asyncio
from decimal import Decimal
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 数据库连接（从 .env 读取）
DATABASE_URL = "postgresql+asyncpg://salmon:001978@localhost:5432/salmon_pms"

async def fix_sales_net_amount():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # 1. 查找所有不一致的记录
        result = await conn.execute(text("""
            SELECT 
                id, sale_no, gross_amount, scan_fee, rounding_adjustment,
                after_sales_adjustment, discount, commission, net_amount,
                gross_amount - COALESCE(scan_fee, 0) - COALESCE(rounding_adjustment, 0) 
                - COALESCE(after_sales_adjustment, 0) - COALESCE(discount, 0) 
                - COALESCE(commission, 0) AS expected_net
            FROM whole_fish_sales
            WHERE ABS(
                net_amount - (
                    gross_amount - COALESCE(scan_fee, 0) - COALESCE(rounding_adjustment, 0) 
                    - COALESCE(after_sales_adjustment, 0) - COALESCE(discount, 0) 
                    - COALESCE(commission, 0)
                )
            ) > 0.01
            ORDER BY id
        """))
        
        rows = result.all()
        if not rows:
            print("✅ 所有销售单 net_amount 一致，无需修复")
            return
        
        print(f"⚠️ 发现 {len(rows)} 条不一致的销售单，开始修复...\n")
        
        fixed_count = 0
        total_diff = Decimal("0")
        
        for row in rows:
            sale_id = row.id
            expected = row.gross_amount - (row.scan_fee or 0) - (row.rounding_adjustment or 0) - (row.after_sales_adjustment or 0) - (row.discount or 0) - (row.commission or 0)
            diff = row.net_amount - expected
            total_diff += diff
            
            # 修复 net_amount
            await conn.execute(
                text("""
                    UPDATE whole_fish_sales
                    SET net_amount = :expected,
                        updated_at = NOW()
                    WHERE id = :sale_id
                """),
                {"expected": float(expected), "sale_id": sale_id}
            )
            
            # 同时检查并同步收款状态
            paid_result = await conn.execute(
                text("""
                    SELECT COALESCE(SUM(amount), 0) as total_paid
                    FROM sales_receipts
                    WHERE sale_id = :sale_id
                """),
                {"sale_id": sale_id}
            )
            paid_row = paid_result.first()
            total_paid = paid_row.total_paid if paid_row else 0
            
            new_status = "PENDING"
            if total_paid >= expected and expected > 0:
                new_status = "FULLY_PAID"
            elif total_paid > 0:
                new_status = "PARTIAL_PAID"
            
            # 如果 paid_amount 也不一致，同步修复
            await conn.execute(
                text("""
                    UPDATE whole_fish_sales
                    SET paid_amount = :paid,
                        status = :status
                    WHERE id = :sale_id
                """),
                {"paid": float(total_paid), "status": new_status, "sale_id": sale_id}
            )
            
            fixed_count += 1
            print(f"  ✅ 修复 ID={sale_id} ({row.sale_no}): {row.net_amount:.2f} → {expected:.2f} (差异: {diff:.2f})")
        
        await conn.commit()
        
        print(f"\n✅ 修复完成: {fixed_count} 条记录已修复")
        print(f"📊 总差异: {float(total_diff):.2f}")

if __name__ == "__main__":
    asyncio.run(fix_sales_net_amount())
