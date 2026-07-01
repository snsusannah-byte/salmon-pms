#!/usr/bin/env python3
"""调试脚本：检查 related_invoice_ids 的类型"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

async def debug():
    engine = create_async_engine('postgresql+asyncpg://salmon:001978@localhost:5432/salmon_pms')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        from app.models.batch import ExchangeRecord
        result = await db.execute(
            select(ExchangeRecord).where(ExchangeRecord.related_invoice_ids.isnot(None))
        )
        exchanges = list(result.scalars().all())
        
        for ex in exchanges[:3]:
            print(f"exchange_no={ex.exchange_no}")
            print(f"  related_invoice_ids={ex.related_invoice_ids}")
            print(f"  type={type(ex.related_invoice_ids)}")
            if ex.related_invoice_ids:
                print(f"  first_elem_type={type(ex.related_invoice_ids[0]) if len(ex.related_invoice_ids) > 0 else 'empty'}")
            print()

if __name__ == "__main__":
    asyncio.run(debug())
