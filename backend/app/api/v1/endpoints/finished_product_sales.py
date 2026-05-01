from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.models import SalesStatus, FinishedProductSale, Company, Product, User
from app.schemas.finished_product_sales import (
    FinishedProductSaleCreate,
    FinishedProductSaleUpdate,
    FinishedProductSaleResponse,
    FinishedProductSaleListResponse,
    FinishedProductSaleSummary,
)
from app.services.finished_product_sale_service import FinishedProductSaleService

router = APIRouter()


async def _build_sale_response(db: AsyncSession, sale: FinishedProductSale) -> FinishedProductSaleResponse:
    """构建成品销售响应（含关联信息）"""
    customer_name = None
    product_name = None
    product_spec = None
    salesperson_name = None

    if sale.customer_id:
        r = await db.execute(select(Company.name).where(Company.id == sale.customer_id))
        customer_name = r.scalar()
    if sale.product_id:
        r = await db.execute(select(Product.name, Product.spec).where(Product.id == sale.product_id))
        product_row = r.one_or_none()
        if product_row:
            product_name = product_row[0]
            product_spec = product_row[1]
    if sale.salesperson_id:
        r = await db.execute(select(User.full_name).where(User.id == sale.salesperson_id))
        salesperson_name = r.scalar()

    return FinishedProductSaleResponse(
        id=sale.id,
        sale_date=sale.sale_date,
        customer_id=sale.customer_id,
        product_id=sale.product_id,
        quantity=sale.quantity,
        unit_price=sale.unit_price,
        gross_amount=sale.gross_amount,
        scan_fee=sale.scan_fee,
        discount=sale.discount,
        commission=sale.commission,
        net_amount=sale.net_amount,
        paid_amount=sale.paid_amount,
        status=sale.status,
        salesperson_id=sale.salesperson_id,
        notes=sale.notes,
        is_locked=sale.is_locked,
        created_at=sale.created_at,
        updated_at=sale.updated_at,
        customer_name=customer_name,
        product_name=product_name,
        product_spec=product_spec,
        salesperson_name=salesperson_name,
    )


@router.get("/", response_model=FinishedProductSaleListResponse)
async def list_finished_product_sales(
    customer_id: Optional[int] = Query(None, description="客户ID"),
    product_id: Optional[int] = Query(None, description="产品ID"),
    status: Optional[SalesStatus] = Query(None, description="收款状态"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """成品销售列表"""
    items, total = await FinishedProductSaleService.list_sales(
        db=db, customer_id=customer_id, product_id=product_id, status=status, skip=skip, limit=limit
    )
    result_items = []
    for sale in items:
        result_items.append(await _build_sale_response(db, sale))
    return FinishedProductSaleListResponse(total=total, items=result_items, skip=skip, limit=limit)


@router.post("/", response_model=FinishedProductSaleResponse, status_code=status.HTTP_201_CREATED)
async def create_finished_product_sale(
    data: FinishedProductSaleCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建成品销售"""
    sale = await FinishedProductSaleService.create_sale(db, data.model_dump())
    return await _build_sale_response(db, sale)


@router.get("/summary", response_model=FinishedProductSaleSummary)
async def get_finished_product_sales_summary(
    db: AsyncSession = Depends(get_db),
):
    """成品销售汇总统计"""
    summary = await FinishedProductSaleService.get_summary(db)
    return FinishedProductSaleSummary(**summary)


@router.get("/{sale_id}", response_model=FinishedProductSaleResponse)
async def get_finished_product_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """成品销售详情"""
    sale = await FinishedProductSaleService.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    return await _build_sale_response(db, sale)


@router.put("/{sale_id}", response_model=FinishedProductSaleResponse)
async def update_finished_product_sale(
    sale_id: int,
    data: FinishedProductSaleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新成品销售"""
    sale = await FinishedProductSaleService.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    update_data = data.model_dump(exclude_unset=True)
    updated = await FinishedProductSaleService.update_sale(db, sale, update_data)
    return await _build_sale_response(db, updated)


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finished_product_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除成品销售"""
    sale = await FinishedProductSaleService.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    await FinishedProductSaleService.delete_sale(db, sale)
    return None
