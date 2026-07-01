#!/usr/bin/env python3
"""精确测试 total_exchanged_usd 计算"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def test():
    engine = create_async_engine('postgresql+asyncpg://salmon:001978@localhost:5432/salmon_pms')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        from app.api.v1.endpoints.reports import list_payable_statements
        result = await list_payable_statements(
            skip=0, limit=500,
            start_date="2026-01-01", end_date="2026-06-30",
            purchase_type="import",
            importer_id=80,
            supplier_id=61,
            db=db
        )
        for item in result.items[:1]:
            print(f"Supplier: {item.supplier_name}")
            print(f"total_exchanged_usd from API: {item.total_exchanged_usd}")
            print(f"\nAll exchange_details amount_usd:")
            total = 0
            for i, ed in enumerate(item.exchange_details):
                print(f"  {i+1}. {ed.exchange_no}: amount_usd={ed.amount_usd}, type={type(ed.amount_usd)}")
                total += ed.amount_usd
            print(f"\nManual sum: {total}")
            print(f"Difference: {item.total_exchanged_usd - total}")

if __name__ == "__main__":
    asyncio.run(test())
