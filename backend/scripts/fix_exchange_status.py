#!/usr/bin/env python3
"""
修复脚本：重新计算所有发票的 exchange_status
用途：修复因 Decimal 精度问题导致的 partial → completed 错误

运行方式（在 backend 目录下）：
    python -m scripts.fix_exchange_status

或直接：
    python scripts/fix_exchange_status.py
"""

import asyncio
import sys
from pathlib import Path

# 将 backend 加入路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.services.finance_service import FinanceService
from app.models import ImportInvoice
from sqlalchemy import select


async def fix_all_exchange_statuses():
    """重新计算所有发票的购汇状态"""
    async with async_session_maker() as db:
        # 查询所有发票
        result = await db.execute(select(ImportInvoice.id))
        all_ids = [row[0] for row in result.all()]
        
        print(f"共 {len(all_ids)} 张发票需要检查...")
        
        fixed = 0
        checked = 0
        
        for invoice_id in all_ids:
            # 使用服务层的单发票状态更新逻辑
            await FinanceService._update_invoice_exchange_status(db, invoice_id=invoice_id)
            
            # 查询更新后的状态
            result = await db.execute(
                select(ImportInvoice.exchange_status, ImportInvoice.invoice_no)
                .where(ImportInvoice.id == invoice_id)
            )
            row = result.one_or_none()
            if row:
                status, invoice_no = row
                checked += 1
                if status in ("completed", "partial"):
                    fixed += 1
                    print(f"  [{status}] {invoice_no}")
        
        print(f"\n完成：检查了 {checked} 张发票，其中 {fixed} 张有购汇记录。")


if __name__ == "__main__":
    asyncio.run(fix_all_exchange_statuses())
