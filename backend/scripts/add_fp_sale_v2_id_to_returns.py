#!/usr/bin/env python3
"""给 return_orders 表添加 finished_product_sale_v2_id 字段"""
from sqlalchemy import text

async def add_finished_product_sale_v2_id():
    from app.core.database import engine
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'return_orders'
            AND column_name = 'finished_product_sale_v2_id'
        """))
        if result.scalar_one_or_none():
            print("finished_product_sale_v2_id 已存在，跳过")
            return

        await conn.execute(text("""
            ALTER TABLE return_orders
            ADD COLUMN finished_product_sale_v2_id INTEGER,
            ADD CONSTRAINT fk_return_orders_finished_sale_v2
            FOREIGN KEY (finished_product_sale_v2_id) REFERENCES finished_product_sales_v2(id)
            ON DELETE SET NULL
        """))
        print("finished_product_sale_v2_id 字段添加成功")

if __name__ == "__main__":
    import asyncio
    asyncio.run(add_finished_product_sale_v2_id())
