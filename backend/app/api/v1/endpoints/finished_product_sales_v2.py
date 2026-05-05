from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import FinishedProductSale, Product
from app.models.finished_product_v2 import FinishedProductSaleItem, SaleItemType
from app.schemas.finished_product_v2 import (
    FinishedProductSaleItemResponse,
    FinishedProductSaleItemCreate,
    SlaughterDateOption,
    FinishedProductSaleWithItemsCreate,
)
from app.services.daily_slaughter_service import DailySlaughterService
from app.services.finished_product_sale_v2 import FinishedProductSaleServiceV2

router = APIRouter()


@router.post("/with-items", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_sale_with_items(
    data: FinishedProductSaleWithItemsCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建成品销售（带子项）
    
    - slaughter_date: 关联的宰杀日期（必须已锁定且有可用肉）
    - total_weight_kg: 销售总重量（kg）
    - items: 销售子项列表 [{item_type, product_id, weight_kg/quantity, unit_price}]
      * item_type: main(正品按kg) / gift(赠品按件) / accessory(配套按件)
    """
    sale_data = data.model_dump(exclude={"items"})
    items = data.items or []
    
    # 如果没有提供子项，默认创建一个正品子项
    if not items and sale_data.get("total_weight_kg"):
        items = [{
            "item_type": SaleItemType.MAIN.value,
            "product_id": sale_data["product_id"],
            "weight_kg": sale_data["total_weight_kg"],
            "unit_price": sale_data["unit_price"],
        }]
    
    try:
        sale = await FinishedProductSaleServiceV2.create_sale_with_items(db, sale_data, items)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 构建响应
    return {
        "id": sale.id,
        "sale_date": sale.sale_date,
        "customer_id": sale.customer_id,
        "product_id": sale.product_id,
        "quantity": sale.quantity,
        "unit_price": sale.unit_price,
        "gross_amount": sale.gross_amount,
        "net_amount": sale.net_amount,
        "slaughter_date": sale.slaughter_date,
        "total_weight_kg": sale.total_weight_kg,
        "status": sale.status,
        "created_at": sale.created_at,
    }


@router.get("/options/slaughter-dates", response_model=List[SlaughterDateOption])
async def get_available_slaughter_dates(
    min_available_kg: Optional[Decimal] = Query(Decimal("0")),
    db: AsyncSession = Depends(get_db),
):
    """获取可供销售的宰杀日期列表"""
    dates = await DailySlaughterService.get_available_slaughter_dates(db, min_available_kg)
    return [SlaughterDateOption(**d) for d in dates]


@router.get("/{sale_id}/items", response_model=List[FinishedProductSaleItemResponse])
async def get_sale_items(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取销售子项列表"""
    items = await FinishedProductSaleServiceV2.get_sale_items(db, sale_id)
    return [FinishedProductSaleItemResponse.model_validate(i) for i in items]
