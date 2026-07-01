#!/usr/bin/env python3
"""直接测试 list_payable_statements API"""

import asyncio
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def test():
    engine = create_async_engine('postgresql+asyncpg://salmon:001978@localhost:5432/salmon_pms')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            from app.api.v1.endpoints.reports import list_payable_statements
            result = await list_payable_statements(
                skip=0, limit=500,
                start_date="2025-01-01", end_date="2026-06-30",
                purchase_type="import",
                importer_id=80,
                supplier_id=61,
                db=db
            )
            print(f"Total items: {result.total}")
            for item in result.items[:1]:
                print(f"Supplier: {item.supplier_name}")
                print(f"Exchange details: {len(item.exchange_details)}")
                for ed in item.exchange_details[:5]:
                    print(f"  购汇 {ed.exchange_no}: 日期={ed.exchange_date}, USD={ed.amount_usd}, invoice_nos={ed.invoice_nos}")
                print(f"\n汇总:")
                print(f"  total_import_usd={item.total_import_usd}")
                print(f"  total_exchanged_usd={item.total_exchanged_usd}")
                print(f"  total_unexchanged_usd={item.total_unexchanged_usd}")
                print(f"  total_exchanged_cny={item.total_exchanged_cny}")
        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
