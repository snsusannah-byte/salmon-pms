from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.models import SalesStatus, WholeFishSale, SalesReceipt, AftersalesRecord, Company, Batch, User
from app.schemas.sales import (
    WholeFishSaleCreate,
    WholeFishSaleUpdate,
    WholeFishSaleResponse,
    WholeFishSaleListResponse,
    SalesReceiptCreate,
    SalesReceiptUpdate,
    SalesReceiptResponse,
    AftersalesRecordCreate,
    AftersalesRecordUpdate,
    AftersalesRecordResponse,
    SaleSummary,
)
from app.services.sales_service import SalesService

router = APIRouter()


async def _build_sale_response(db: AsyncSession, sale: WholeFishSale) -> WholeFishSaleResponse:
    """构建销售响应（含关联信息）"""
    customer_name = None
    batch_name = None
    batch_code = None
    salesperson_name = None

    if sale.customer_id:
        r = await db.execute(select(Company.name).where(Company.id == sale.customer_id))
        customer_name = r.scalar()
    if sale.batch_id:
        r = await db.execute(select(Batch.batch_name, Batch.batch_code).where(Batch.id == sale.batch_id))
        batch_row = r.one_or_none()
        if batch_row:
            batch_name = batch_row[0]
            batch_code = batch_row[1]
    if sale.salesperson_id:
        r = await db.execute(select(User.full_name).where(User.id == sale.salesperson_id))
        salesperson_name = r.scalar()

    receipts = [
        SalesReceiptResponse.model_validate(r) for r in (sale.receipts or [])
    ]
    aftersales = [
        AftersalesRecordResponse.model_validate(a) for a in (sale.aftersales_records or [])
    ]

    return WholeFishSaleResponse(
        id=sale.id,
        batch_id=sale.batch_id,
        sale_date=sale.sale_date,
        customer_id=sale.customer_id,
        weight_kg=sale.weight_kg,
        unit_price=sale.unit_price,
        gross_amount=sale.gross_amount,
        scan_fee=sale.scan_fee,
        rounding_adjustment=sale.rounding_adjustment,
        after_sales_adjustment=sale.after_sales_adjustment,
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
        batch_name=batch_name,
        batch_code=batch_code,
        salesperson_name=salesperson_name,
        receipts=receipts,
        aftersales=aftersales,
    )


# ==================== 整鱼销售 ====================

@router.get("/whole-fish", response_model=WholeFishSaleListResponse)
async def list_whole_fish_sales(
    batch_id: Optional[int] = Query(None, description="批次ID"),
    customer_id: Optional[int] = Query(None, description="客户ID"),
    status: Optional[SalesStatus] = Query(None, description="收款状态"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """整鱼销售列表"""
    items, total = await SalesService.list_sales(
        db=db, batch_id=batch_id, customer_id=customer_id, status=status, skip=skip, limit=limit
    )
    result_items = []
    for sale in items:
        result_items.append(await _build_sale_response(db, sale))
    return WholeFishSaleListResponse(total=total, items=result_items, skip=skip, limit=limit)


@router.post("/whole-fish", response_model=WholeFishSaleResponse, status_code=status.HTTP_201_CREATED)
async def create_whole_fish_sale(
    data: WholeFishSaleCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建整鱼销售"""
    sale = await SalesService.create_sale(db, data.model_dump())
    return await _build_sale_response(db, sale)


@router.get("/whole-fish/{sale_id}", response_model=WholeFishSaleResponse)
async def get_whole_fish_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """整鱼销售详情"""
    sale = await SalesService.get_sale_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    return await _build_sale_response(db, sale)


@router.put("/whole-fish/{sale_id}", response_model=WholeFishSaleResponse)
async def update_whole_fish_sale(
    sale_id: int,
    data: WholeFishSaleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新整鱼销售"""
    sale = await SalesService.get_sale_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    update_data = data.model_dump(exclude_unset=True)
    updated = await SalesService.update_sale(db, sale, update_data)
    return await _build_sale_response(db, updated)


@router.delete("/whole-fish/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_whole_fish_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除整鱼销售"""
    sale = await SalesService.get_sale_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    await SalesService.delete_sale(db, sale)
    return None


# ==================== 收款记录 ====================

@router.get("/whole-fish/{sale_id}/receipts", response_model=List[SalesReceiptResponse])
async def list_sale_receipts(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """收款记录列表"""
    sale = await SalesService.get_sale_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    return [SalesReceiptResponse.model_validate(r) for r in (sale.receipts or [])]


@router.post("/whole-fish/{sale_id}/receipts", response_model=SalesReceiptResponse, status_code=status.HTTP_201_CREATED)
async def create_sale_receipt(
    sale_id: int,
    data: SalesReceiptCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建收款记录"""
    receipt = await SalesService.add_receipt(db, sale_id, data.model_dump())
    return SalesReceiptResponse.model_validate(receipt)


@router.delete("/whole-fish/{sale_id}/receipts/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale_receipt(
    sale_id: int,
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除收款记录"""
    await SalesService.delete_receipt(db, receipt_id)
    return None


# ==================== 售后记录 ====================

@router.get("/whole-fish/{sale_id}/aftersales", response_model=List[AftersalesRecordResponse])
async def list_aftersales(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """售后记录列表"""
    sale = await SalesService.get_sale_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    return [AftersalesRecordResponse.model_validate(a) for a in (sale.aftersales_records or [])]


@router.post("/whole-fish/{sale_id}/aftersales", response_model=AftersalesRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_aftersales(
    sale_id: int,
    data: AftersalesRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建售后记录"""
    record = await SalesService.add_aftersales(db, sale_id, data.model_dump())
    return AftersalesRecordResponse.model_validate(record)


@router.put("/whole-fish/{sale_id}/aftersales/{record_id}", response_model=AftersalesRecordResponse)
async def update_aftersales(
    sale_id: int,
    record_id: int,
    data: AftersalesRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新售后记录"""
    result = await db.execute(select(AftersalesRecord).where(AftersalesRecord.id == record_id, AftersalesRecord.sale_id == sale_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="售后记录不存在")
    update_data = data.model_dump(exclude_unset=True)
    updated = await SalesService.update_aftersales(db, record, update_data)
    return AftersalesRecordResponse.model_validate(updated)


@router.delete("/whole-fish/{sale_id}/aftersales/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aftersales(
    sale_id: int,
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除售后记录"""
    await SalesService.delete_aftersales(db, record_id)
    return None


# ==================== 汇总 ====================

@router.get("/summary", response_model=SaleSummary)
async def get_sales_summary(
    db: AsyncSession = Depends(get_db),
):
    """销售汇总统计"""
    summary = await SalesService.get_summary(db)
    return SaleSummary(**summary)


# ==================== 批量导入 ====================

@router.post("/batch-import", status_code=status.HTTP_201_CREATED)
async def batch_import_sales(
    records: List[dict],
    db: AsyncSession = Depends(get_db),
):
    """批量导入整鱼销售记录
    
    每行数据需要包含: customer_name, sale_date, weight_kg, unit_price
    自动查找或创建客户，自动计算金额
    返回: {created: 新增数, errors: 错误列表, items: 销售列表}
    """
    from app.services.company_service import CompanyService
    from app.services.batch_service import BatchService
    from decimal import Decimal
    from datetime import date, datetime
    
    created_count = 0
    result_items = []
    errors = []
    
    for idx, record in enumerate(records):
        try:
            customer_name = record.get("customer_name", "").strip()
            if not customer_name:
                errors.append({"row": idx + 1, "error": "客户名称不能为空"})
                continue
            
            # 查找或创建客户
            customer = await CompanyService.get_or_create_customer(
                db=db,
                name=customer_name,
                contact_person=record.get("contact_person"),
                phone=record.get("phone"),
                address=record.get("address"),
                customer_category=record.get("customer_category"),
            )
            
            # 解析批次（按 batch_code 查找）
            batch_id = None
            batch_code = record.get("batch_code", "").strip()
            if batch_code:
                batch = await BatchService.get_by_code(db, batch_code)
                if batch:
                    batch_id = batch.id
            
            # 解析销售日期
            sale_date_str = record.get("sale_date", "").strip()
            sale_date = date.today()
            if sale_date_str:
                try:
                    sale_date = datetime.strptime(sale_date_str, "%Y-%m-%d").date()
                except ValueError:
                    try:
                        sale_date = datetime.strptime(sale_date_str, "%Y/%m/%d").date()
                    except ValueError:
                        pass
            
            # 解析重量和单价
            weight_kg = Decimal(str(record.get("weight_kg", 0)))
            unit_price = Decimal(str(record.get("unit_price", 0)))
            scan_fee = Decimal(str(record.get("scan_fee", 0)))
            
            # 计算金额
            gross_amount = (weight_kg * unit_price).quantize(Decimal("0.01"))
            net_amount = gross_amount - scan_fee
            
            # 创建销售记录
            sale_data = {
                "customer_id": customer.id,
                "batch_id": batch_id,
                "sale_date": sale_date,
                "weight_kg": weight_kg,
                "unit_price": unit_price,
                "gross_amount": gross_amount,
                "scan_fee": scan_fee,
                "net_amount": net_amount,
                "paid_amount": Decimal("0"),
                "status": "pending",
                "notes": record.get("notes", ""),
            }
            
            sale = await SalesService.create_sale(db, sale_data)
            created_count += 1
            result_items.append(await _build_sale_response(db, sale))
            
        except Exception as e:
            errors.append({"row": idx + 1, "error": str(e)})
    
    return {
        "created": created_count,
        "errors": errors,
        "items": result_items,
    }
