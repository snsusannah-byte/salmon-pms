#!/usr/bin/env python3
"""给 finished_product_receipts 表添加 transaction_id 字段"""
from sqlalchemy import text

async def add_transaction_id():
    from app.core.database import engine
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'finished_product_receipts'
            AND column_name = 'transaction_id'
        """))
        if result.scalar_one_or_none():
            print("transaction_id 已存在，跳过")
            return

        await conn.execute(text("""
            ALTER TABLE finished_product_receipts
            ADD COLUMN transaction_id INTEGER,
            ADD CONSTRAINT fk_receipts_transaction
            FOREIGN KEY (transaction_id) REFERENCES transaction_records(id)
            ON DELETE SET NULL
        """))
        print("transaction_id 字段添加成功")

if __name__ == "__main__":
    import asyncio
    asyncio.run(add_transaction_id())
