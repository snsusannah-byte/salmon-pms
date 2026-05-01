from decimal import Decimal
from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import InvoiceStatus, ExchangeStatus
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceProductCreate,
    InvoiceProductUpdate,
    InvoiceProductResponse,
    InvoiceSummary,
)
from app.services.invoice_service import InvoiceService

router = APIRouter()


@router.get("/", response_model=InvoiceListResponse)
async def list_invoices(
    customs_status: Optional[InvoiceStatus] = Query(None, description="报关状态"),
    exchange_status: Optional[ExchangeStatus] = Query(None, description="购汇状态"),
    processing_plant_id: Optional[int] = Query(None, description="加工厂ID"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    search: Optional[str] = Query(None, description="搜索发票编号"),
    exclude_assigned: bool = Query(False, description="排除已关联批次的发票"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """发票列表
    
    - **customs_status**: 按报关状态筛选
    - **exchange_status**: 按购汇状态筛选
    - **processing_plant_id**: 按加工厂筛选
    - **start_date/end_date**: 按日期范围筛选
    - **search**: 按发票编号搜索
    - **exclude_assigned**: 排除已关联批次的发票（用于批次创建时选择）
    """
    items, total = await InvoiceService.list_invoices(
        db=db,
        customs_status=customs_status,
        exchange_status=exchange_status,
        processing_plant_id=processing_plant_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        exclude_assigned=exclude_assigned,
        skip=skip,
        limit=limit,
    )
    
    # 填充关联名称
    result_items = []
    for item in items:
        # 手动查询产品明细
        from sqlalchemy import select
        from app.models import InvoiceProduct
        
        product_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == item.id)
        )
        products = product_result.scalars().all()
        
        # 手动构建响应对象
        item_dict = {
            "id": item.id,
            "invoice_no": item.invoice_no,
            "invoice_date": item.invoice_date,
            "kill_date": item.kill_date,
            "arrival_date": item.arrival_date,
            "processing_plant_id": item.processing_plant_id,
            "fish_farm_id": item.fish_farm_id,
            "exporter_id": item.exporter_id,
            "total_amount_usd": item.total_amount_usd,
            "total_boxes": item.total_boxes,
            "total_weight_kg": item.total_weight_kg,
            "awb_no": item.awb_no,
            "gross_weight_kg": item.gross_weight_kg,
            "eta": item.eta,
            "departure_date": item.departure_date,
            "flight_info": item.flight_info,
            "origin_certificate": item.origin_certificate,
            "inspection_certificate": item.inspection_certificate,
            "customs_status": item.customs_status,
            "exchange_status": item.exchange_status,
            "is_locked": item.is_locked,
            "notes": item.notes,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "processing_plant_name": None,
            "processing_plant_code": None,
            "fish_farm_name": None,
            "fish_farm_code": None,
            "exporter_name": None,
            "exporter_code": None,
            "products": [],
        }
        
        # 查询关联的公司名称和编号
        from app.models import Company
        if item.processing_plant_id:
            company_result = await db.execute(
                select(Company.name, Company.code).where(Company.id == item.processing_plant_id)
            )
            row = company_result.one_or_none()
            if row:
                item_dict["processing_plant_name"] = row[0]
                item_dict["processing_plant_code"] = row[1]
        
        if item.fish_farm_id:
            company_result = await db.execute(
                select(Company.name, Company.code).where(Company.id == item.fish_farm_id)
            )
            row = company_result.one_or_none()
            if row:
                item_dict["fish_farm_name"] = row[0]
                item_dict["fish_farm_code"] = row[1]
        
        if item.exporter_id:
            company_result = await db.execute(
                select(Company.name, Company.code).where(Company.id == item.exporter_id)
            )
            row = company_result.one_or_none()
            if row:
                item_dict["exporter_name"] = row[0]
                item_dict["exporter_code"] = row[1]
        
        # 添加产品明细，并实时汇总计算总箱数/总金额
        computed_boxes = 0
        computed_amount = Decimal("0")
        for p in products:
            item_dict["products"].append({
                "id": p.id,
                "invoice_id": p.invoice_id,
                "product_name": p.product_name,
                "product_spec": p.product_spec,
                "box_count": p.box_count,
                "net_weight_kg": p.net_weight_kg,
                "unit_price": p.unit_price,
                "total_amount": p.total_amount,
                "notes": p.notes,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            })
            computed_boxes += p.box_count or 0
            computed_amount += Decimal(p.total_amount or 0)
        
        # 如果数据库中汇总字段为0，使用计算值
        if item_dict["total_boxes"] == 0 and computed_boxes > 0:
            item_dict["total_boxes"] = computed_boxes
        if item_dict["total_amount_usd"] == 0 and computed_amount > 0:
            item_dict["total_amount_usd"] = computed_amount
        
        result_items.append(InvoiceResponse(**item_dict))
    
    return InvoiceListResponse(
        total=total,
        items=result_items,
        skip=skip,
        limit=limit,
    )


@router.get("/summary", response_model=InvoiceSummary)
async def get_invoice_summary(
    db: AsyncSession = Depends(get_db),
):
    """发票汇总统计"""
    summary = await InvoiceService.get_summary(db)
    return InvoiceSummary(**summary)


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建发票（含产品明细）"""
    # 检查发票编号是否重复
    existing = await InvoiceService.get_by_invoice_no(db, data.invoice_no)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"发票编号 '{data.invoice_no}' 已存在",
        )
    
    invoice = await InvoiceService.create(db, data)
    
    # 手动构建响应
    from sqlalchemy import select
    from app.models import Company, InvoiceProduct
    
    result = {
        "id": invoice.id,
        "invoice_no": invoice.invoice_no,
        "invoice_date": invoice.invoice_date,
        "kill_date": invoice.kill_date,
        "arrival_date": invoice.arrival_date,
        "processing_plant_id": invoice.processing_plant_id,
        "fish_farm_id": invoice.fish_farm_id,
        "exporter_id": invoice.exporter_id,
        "total_amount_usd": invoice.total_amount_usd,
        "total_boxes": invoice.total_boxes,
        "total_weight_kg": invoice.total_weight_kg,
        "awb_no": invoice.awb_no,
        "customs_status": invoice.customs_status,
        "exchange_status": invoice.exchange_status,
        "is_locked": invoice.is_locked,
        "notes": invoice.notes,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "processing_plant_name": None,
        "processing_plant_code": None,
        "fish_farm_name": None,
        "fish_farm_code": None,
        "exporter_name": None,
        "exporter_code": None,
        "products": [],
    }
    
    # 查询关联名称和编号
    if invoice.processing_plant_id:
        company_result = await db.execute(
            select(Company.name, Company.code).where(Company.id == invoice.processing_plant_id)
        )
        row = company_result.one_or_none()
        if row:
            result["processing_plant_name"] = row[0]
            result["processing_plant_code"] = row[1]
    
    if invoice.exporter_id:
        company_result = await db.execute(
            select(Company.name, Company.code).where(Company.id == invoice.exporter_id)
        )
        row = company_result.one_or_none()
        if row:
            result["exporter_name"] = row[0]
            result["exporter_code"] = row[1]
    
    # 查询产品明细
    product_result = await db.execute(
        select(InvoiceProduct).where(InvoiceProduct.invoice_id == invoice.id)
    )
    products = product_result.scalars().all()
    
    for p in products:
        result["products"].append({
            "id": p.id,
            "invoice_id": p.invoice_id,
            "product_name": p.product_name,
            "product_spec": p.product_spec,
            "box_count": p.box_count,
            "net_weight_kg": p.net_weight_kg,
            "unit_price": p.unit_price,
            "total_amount": p.total_amount,
            "notes": p.notes,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        })
    
    return InvoiceResponse(**result)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """发票详情（含产品明细）"""
    invoice = await InvoiceService.get_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"发票 ID={invoice_id} 不存在",
        )
    
    # Manually construct dict to avoid ORM relationship mapping issues
    invoice_dict = {
        "id": invoice.id,
        "invoice_no": invoice.invoice_no,
        "invoice_date": invoice.invoice_date,
        "kill_date": invoice.kill_date,
        "arrival_date": invoice.arrival_date,
        "processing_plant_id": invoice.processing_plant_id,
        "fish_farm_id": invoice.fish_farm_id,
        "exporter_id": invoice.exporter_id,
        "total_amount_usd": invoice.total_amount_usd,
        "total_boxes": invoice.total_boxes,
        "total_weight_kg": invoice.total_weight_kg,
        "awb_no": invoice.awb_no,
        "gross_weight_kg": invoice.gross_weight_kg,
        "eta": invoice.eta,
        "departure_date": invoice.departure_date,
        "flight_info": invoice.flight_info,
        "origin_certificate": invoice.origin_certificate,
        "inspection_certificate": invoice.inspection_certificate,
        "customs_status": invoice.customs_status,
        "exchange_status": invoice.exchange_status,
        "is_locked": invoice.is_locked,
        "notes": invoice.notes,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "processing_plant_name": invoice.processing_plant.name if invoice.processing_plant else None,
        "fish_farm_name": invoice.fish_farm.name if invoice.fish_farm else None,
        "exporter_name": invoice.exporter.name if invoice.exporter else None,
        "products": [],
    }
    
    # Handle products - SQLAlchemy may return single object instead of list
    products = invoice.products
    if products:
        # If it's a single object, wrap in list
        if not isinstance(products, list):
            products = [products]
        invoice_dict["products"] = [InvoiceProductResponse.model_validate(p) for p in products]
    
    result = InvoiceResponse(**invoice_dict)
    return result


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新发票"""
    invoice = await InvoiceService.get_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"发票 ID={invoice_id} 不存在",
        )
    
    updated = await InvoiceService.update(db, invoice, data)
    return InvoiceResponse.model_validate(updated)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除发票"""
    invoice = await InvoiceService.get_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"发票 ID={invoice_id} 不存在",
        )
    
    await InvoiceService.delete(db, invoice)
    return None


# ==================== 锁定/解锁 ====================

@router.post("/{invoice_id}/lock", response_model=InvoiceResponse)
async def lock_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """锁定发票"""
    invoice = await InvoiceService.get_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"发票 ID={invoice_id} 不存在",
        )
    
    invoice.is_locked = True
    await db.commit()
    await db.refresh(invoice)
    return InvoiceResponse.model_validate(invoice)


@router.post("/{invoice_id}/unlock", response_model=InvoiceResponse)
async def unlock_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """解锁发票"""
    invoice = await InvoiceService.get_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"发票 ID={invoice_id} 不存在",
        )
    
    invoice.is_locked = False
    await db.commit()
    await db.refresh(invoice)
    return InvoiceResponse.model_validate(invoice)


# ==================== 产品明细 ====================

@router.post("/{invoice_id}/products", response_model=InvoiceProductResponse)
async def add_invoice_product(
    invoice_id: int,
    data: InvoiceProductCreate,
    db: AsyncSession = Depends(get_db),
):
    """添加产品明细"""
    product = await InvoiceService.add_product(db, invoice_id, data)
    return InvoiceProductResponse.model_validate(product)


@router.put("/{invoice_id}/products/{product_id}", response_model=InvoiceProductResponse)
async def update_invoice_product(
    invoice_id: int,
    product_id: int,
    data: InvoiceProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新产品明细"""
    from sqlalchemy import select
    from app.models import InvoiceProduct
    
    result = await db.execute(
        select(InvoiceProduct).where(
            InvoiceProduct.id == product_id,
            InvoiceProduct.invoice_id == invoice_id,
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品明细 ID={product_id} 不存在",
        )
    
    updated = await InvoiceService.update_product(db, product, data)
    return InvoiceProductResponse.model_validate(updated)


@router.delete("/{invoice_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice_product(
    invoice_id: int,
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除产品明细"""
    from sqlalchemy import select
    from app.models import InvoiceProduct
    
    result = await db.execute(
        select(InvoiceProduct).where(
            InvoiceProduct.id == product_id,
            InvoiceProduct.invoice_id == invoice_id,
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品明细 ID={product_id} 不存在",
        )
    
    await InvoiceService.delete_product(db, product)
    return None

