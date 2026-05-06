#!/usr/bin/env python3
"""
清理：删除迁移脚本自动创建的威揽报关行公司(id=62)，
保留用户手动创建的威揽供应商(id=15)。
"""

import asyncio
import sys
sys.path.insert(0, "/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend")

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def cleanup():
    from app.core.database import engine
    
    async with engine.begin() as conn:
        # 1. 确认 id=62 是迁移脚本创建的威揽
        result = await conn.execute(
            text("SELECT id, name, type, code FROM companies WHERE id = 62")
        )
        row = result.one_or_none()
        if not row:
            print("ID 62 not found. Nothing to delete.")
            return

        print(f"Found company to delete: id={row.id}, name={row.name}, type={row.type}, code={row.code}")

        # 2. 检查是否有其他表外键引用 id=62（直接查询，用单独连接避免事务污染）
        check_cols = [
            ("import_invoices", "supplier_id"),
            ("import_invoices", "exporter_id"),
            ("import_invoices", "processing_plant_id"),
            ("import_invoices", "fish_farm_id"),
            ("whole_fish_sales", "customer_id"),
            ("finished_product_sales", "customer_id"),
            ("shipments", "logistics_company_id"),
        ]
        
        for table, col in check_cols:
            try:
                r = await conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {col} = 62"))
                cnt = r.scalar()
                if cnt and cnt > 0:
                    print(f"WARNING: {table}.{col} has {cnt} references to id=62")
            except Exception:
                pass  # 列不存在或表不存在，跳过

        # 3. 删除 id=62
        await conn.execute(text("DELETE FROM companies WHERE id = 62"))
        print("Deleted company id=62 (auto-created customs_broker '威揽').")

        # 4. 确认 id=15 用户手动创建的威揽还在
        r2 = await conn.execute(
            text("SELECT id, name, type, company_full_name FROM companies WHERE id = 15")
        )
        user_row = r2.one_or_none()
        if user_row:
            print(f"Kept user's company: id={user_row.id}, name={user_row.name}, type={user_row.type}, full_name={user_row.company_full_name}")
        else:
            print("WARNING: User's company id=15 not found!")


if __name__ == "__main__":
    asyncio.run(cleanup())
