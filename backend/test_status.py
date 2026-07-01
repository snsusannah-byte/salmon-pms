#!/usr/bin/env python3
"""直接测试 list_payable_statements API - 验证购汇状态"""

import asyncio
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
            for item in result.items[:1]:
                print(f"Supplier: {item.supplier_name}")
                print(f"Exchange details: {len(item.exchange_details)}")
                # 打印前5条采购明细的购汇状态
                for pd in item.purchase_details[:5]:
                    print(f"  发票 {pd.invoice_no}: 状态={pd.exchange_status}, 购汇单号={pd.exchange_no or '-'}")
                # 打印所有购汇明细
                for ed in item.exchange_details[:5]:
                    print(f"  购汇 {ed.exchange_no}: 日期={ed.exchange_date}, USD={ed.amount_usd}")
        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
