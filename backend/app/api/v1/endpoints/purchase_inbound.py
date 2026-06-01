from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime, timedelta
import random

from app.core.database import get_db
from app.models import PurchaseInbound, PurchaseInboundDetail, ImportInvoice, Company, Batch
from app.schemas import PurchaseInboundCreate, PurchaseInboundDetailCreate, PurchaseInboundResponse, PurchaseInboundListResponse
from app.services.purchase_inbound_service import PurchaseInboundService
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User
from app.models.enums import UserRole

router = APIRouter(prefix="/import-inbound", tags=["import-inbound"])

# ... (其他代码保持不变)

@router.delete("/{inbound_id}")
async def delete_purchase_inbound(
    inbound_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.WAREHOUSE])),
):
    """删除采购入库单"""
    inbound = await PurchaseInboundService.get_inbound(db, inbound_id)
    if not inbound:
        raise HTTPException(status_code=404, detail="采购入库单不存在")
    
    await PurchaseInboundService.delete_inbound(db, inbound)
    return {"message": "删除成功"}

# ... (其他代码保持不变)
