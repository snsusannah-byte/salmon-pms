#!/usr/bin/env python3
"""给 finished_product_receipts 表添加 sale_v2_id 字段"""
from sqlalchemy import text

async def add_sale_v2_id():
    from app.core.database import engine
    async with engine.begin() as conn:
        # 检查字段是否存在
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'finished_product_receipts'
            AND column_name = 'sale_v2_id'
        """))
        if result.scalar_one_or_none():
            print("sale_v2_id 已存在，跳过")
            return

        # sale_id 原来是 not null，改成 nullable
        await conn.execute(text("""
            ALTER TABLE finished_product_receipts
            ALTER COLUMN sale_id DROP NOT NULL
        """))

        # 添加 sale_v2_id 字段 + 外键
        await conn.execute(text("""
            ALTER TABLE finished_product_receipts
            ADD COLUMN sale_v2_id INTEGER,
            ADD CONSTRAINT fk_receipts_sale_v2
            FOREIGN KEY (sale_v2_id) REFERENCES finished_product_sales_v2(id)
            ON DELETE CASCADE
        """))
        print("sale_v2_id 字段添加成功")

if __name__ == "__main__":
    import asyncio
    asyncio.run(add_sale_v2_id())
