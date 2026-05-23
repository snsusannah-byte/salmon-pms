#!/usr/bin/env python3
"""
修复脚本：将所有 exchange_status='partial' 的发票改为 'completed'
用途：业务上不存在部分购汇，状态只有 未购汇/已购汇 两种

运行方式（在 backend 目录下）：
    python -m scripts.fix_partial_to_completed

或直接：
    python scripts/fix_partial_to_completed.py
"""

import asyncio
import sys
from pathlib import Path

# 将 backend 加入路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.models import ImportInvoice, ExchangeStatus
from sqlalchemy import select, update


async def fix_partial_to_completed():
    """将所有 partial 状态改为 completed"""
    async with async_session_maker() as db:
        # 查询所有 partial 状态的发票
        result = await db.execute(
            select(ImportInvoice.id, ImportInvoice.invoice_no)
            .where(ImportInvoice.exchange_status == ExchangeStatus.PARTIAL)
        )
        partial_invoices = result.all()
        
        if not partial_invoices:
            print("没有 partial 状态的发票需要修复。")
            return
        
        print(f"发现 {len(partial_invoices)} 张 partial 状态发票，正在修复为 completed...")
        
        # 批量更新
        await db.execute(
            update(ImportInvoice)
            .where(ImportInvoice.exchange_status == ExchangeStatus.PARTIAL)
            .values(exchange_status=ExchangeStatus.COMPLETED)
        )
        await db.commit()
        
        for inv_id, invoice_no in partial_invoices:
            print(f"  ✓ {invoice_no} (ID={inv_id}) → completed")
        
        print(f"\n完成：共修复 {len(partial_invoices)} 张发票。")


if __name__ == "__main__":
    asyncio.run(fix_partial_to_completed())
