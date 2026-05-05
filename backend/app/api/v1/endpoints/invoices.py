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
        
        # 计算产品净重汇总（用于列表页显示真正的净重）
        net_weight_kg_sum = sum(
            Decimal(str(p.net_weight_kg)) for p in products if p.net_weight_kg is not None
        ) if products else Decimal("0")
        
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
            "parent_invoice_id": item.parent_invoice_id,
            "is_master": item.is_master,
            "notes": item.notes,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "net_weight_kg_sum": net_weight_kg_sum,
            "processing_plant_name": None,
            "processing_plant_code": None,
            "fish_farm_name": None,
            "fish_farm_code": None,
            "exporter_name": None,
            "exporter_code": None,
            "parent_invoice_no": None,
            "sub_invoices": [],
            "products": [],
        }
        
        # 查询主票信息
        if item.parent_invoice_id:
            from app.models import ImportInvoice
            parent_result = await db.execute(
                select(ImportInvoice).where(ImportInvoice.id == item.parent_invoice_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent:
                item_dict["parent_invoice_no"] = parent.invoice_no
        
        # 查询子票列表（仅主票）
        if item.is_master:
            from app.models import ImportInvoice
            sub_result = await db.execute(
                select(ImportInvoice).where(ImportInvoice.parent_invoice_id == item.id)
            )
            subs = sub_result.scalars().all()
            for s in subs:
                sub_dict = {
                    "id": s.id,
                    "invoice_no": s.invoice_no,
                    "total_boxes": s.total_boxes,
                    "total_amount_usd": s.total_amount_usd,
                    "total_weight_kg": s.total_weight_kg,
                }
                item_dict["sub_invoices"].append(sub_dict)
        
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
    
    # 手动构建响应（避免 ORM 关系映射问题）
    from sqlalchemy import select
    from app.models import Company, InvoiceProduct
    
    invoice_dict = {
        "id": updated.id,
        "invoice_no": updated.invoice_no,
        "invoice_date": updated.invoice_date,
        "kill_date": updated.kill_date,
        "arrival_date": updated.arrival_date,
        "processing_plant_id": updated.processing_plant_id,
        "fish_farm_id": updated.fish_farm_id,
        "exporter_id": updated.exporter_id,
        "total_amount_usd": updated.total_amount_usd,
        "total_boxes": updated.total_boxes,
        "total_weight_kg": updated.total_weight_kg,
        "awb_no": updated.awb_no,
        "gross_weight_kg": updated.gross_weight_kg,
        "eta": updated.eta,
        "departure_date": updated.departure_date,
        "flight_info": updated.flight_info,
        "origin_certificate": updated.origin_certificate,
        "inspection_certificate": updated.inspection_certificate,
        "customs_status": updated.customs_status,
        "exchange_status": updated.exchange_status,
        "is_locked": updated.is_locked,
        "notes": updated.notes,
        "created_at": updated.created_at,
        "updated_at": updated.updated_at,
        "processing_plant_name": None,
        "processing_plant_code": None,
        "fish_farm_name": None,
        "fish_farm_code": None,
        "exporter_name": None,
        "exporter_code": None,
        "products": [],
    }
    
    # 查询关联名称和编号
    if updated.processing_plant_id:
        company_result = await db.execute(
            select(Company.name, Company.code).where(Company.id == updated.processing_plant_id)
        )
        row = company_result.one_or_none()
        if row:
            invoice_dict["processing_plant_name"] = row[0]
            invoice_dict["processing_plant_code"] = row[1]
    
    if updated.exporter_id:
        company_result = await db.execute(
            select(Company.name, Company.code).where(Company.id == updated.exporter_id)
        )
        row = company_result.one_or_none()
        if row:
            invoice_dict["exporter_name"] = row[0]
            invoice_dict["exporter_code"] = row[1]
    
    # 查询产品明细
    product_result = await db.execute(
        select(InvoiceProduct).where(InvoiceProduct.invoice_id == updated.id)
    )
    products = product_result.scalars().all()
    
    for p in products:
        invoice_dict["products"].append({
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
    
    return InvoiceResponse.model_construct(**invoice_dict)


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


# ==================== 批量导入 ====================

@router.post("/{invoice_id}/allocate-costs", response_model=dict)
async def allocate_costs(
    invoice_id: int,
    clearance_cost: Optional[float] = Query(None, description="清关运费(总额)"),
    import_duty: Optional[float] = Query(None, description="进口关税(总额)"),
    import_vat: Optional[float] = Query(None, description="进口增值税(总额)"),
    allocation_method: str = Query("by_boxes", description="分摊方式: by_boxes / by_weight / by_amount"),
    db: AsyncSession = Depends(get_db),
):
    """
    AWB级别费用分摊 — 按箱数/重量/金额比例分摊到主票和从票
    
    8703（主票，81箱）+ 8710（从票，27箱）共享 AWB:
    清关费 ¥10,000 → 8703 分摊 81/108=¥7,500, 8710 分摊 27/108=¥2,500
    """
    from decimal import Decimal
    from app.models import ImportTax, ClearanceCost, ImportInvoice
    
    # 获取主票
    master = await InvoiceService.get_by_id(db, invoice_id)
    if not master:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    # 检查是否是主票
    if not master.is_master and not master.parent_invoice_id:
        raise HTTPException(status_code=400, detail="请选择一个AWB组的主票进行费用分摊")
    
    # 如果传入的是从票，找到主票
    target_master = master
    if master.parent_invoice_id:
        target_master = await InvoiceService.get_by_id(db, master.parent_invoice_id)
    
    # 获取组内所有发票（主票+从票）
    result = await db.execute(
        select(ImportInvoice).where(
            (ImportInvoice.id == target_master.id) | 
            (ImportInvoice.parent_invoice_id == target_master.id)
        )
    )
    group_invoices = result.scalars().all()
    
    if not group_invoices:
        raise HTTPException(status_code=400, detail="AWB组内没有发票")
    
    # 计算分摊基数
    total_boxes = sum(inv.total_boxes or 0 for inv in group_invoices)
    total_weight = sum(inv.total_weight_kg or Decimal("0") for inv in group_invoices)
    total_amount = sum(inv.total_amount_usd or Decimal("0") for inv in group_invoices)
    
    if total_boxes == 0:
        raise HTTPException(status_code=400, detail="组内发票箱数都为0，无法分摊")
    
    allocated = []
    
    for inv in group_invoices:
        # 计算分摊比例
        if allocation_method == "by_weight" and total_weight > 0:
            ratio = float(inv.total_weight_kg or 0) / float(total_weight)
        elif allocation_method == "by_amount" and total_amount > 0:
            ratio = float(inv.total_amount_usd or 0) / float(total_amount)
        else:
            # 默认按箱数
            ratio = (inv.total_boxes or 0) / total_boxes
        
        # 分摊清关费
        if clearance_cost:
            allocated_clearance = Decimal(str(clearance_cost)) * Decimal(str(ratio))
            
            # 查找或创建 ClearanceCost 记录
            cost_result = await db.execute(
                select(ClearanceCost).where(ClearanceCost.invoice_id == inv.id)
            )
            cost = cost_result.scalar_one_or_none()
            
            if cost:
                cost.clearance_fee = allocated_clearance
                cost.total_cost = allocated_clearance
            else:
                cost = ClearanceCost(
                    invoice_id=inv.id,
                    cost_date=date.today(),
                    clearance_fee=allocated_clearance,
                    total_cost=allocated_clearance,
                    notes=f"AWB费用分摊 ({target_master.invoice_no})"
                )
                db.add(cost)
        
        # 分摊税费
        if import_duty or import_vat:
            allocated_duty = Decimal(str(import_duty or 0)) * Decimal(str(ratio))
            allocated_vat = Decimal(str(import_vat or 0)) * Decimal(str(ratio))
            
            tax_result = await db.execute(
                select(ImportTax).where(ImportTax.invoice_id == inv.id)
            )
            tax = tax_result.scalar_one_or_none()
            
            if tax:
                tax.import_duty = allocated_duty
                tax.import_vat = allocated_vat
                tax.total_tax = allocated_duty + allocated_vat
            else:
                tax = ImportTax(
                    invoice_id=inv.id,
                    tax_date=date.today(),
                    import_duty=allocated_duty,
                    import_vat=allocated_vat,
                    total_tax=allocated_duty + allocated_vat,
                    notes=f"AWB税费分摊 ({target_master.invoice_no})"
                )
                db.add(tax)
        
        allocated.append({
            "invoice_id": inv.id,
            "invoice_no": inv.invoice_no,
            "ratio": round(ratio, 4),
            "clearance_cost": float(Decimal(str(clearance_cost or 0)) * Decimal(str(ratio))) if clearance_cost else None,
            "import_duty": float(Decimal(str(import_duty or 0)) * Decimal(str(ratio))) if import_duty else None,
            "import_vat": float(Decimal(str(import_vat or 0)) * Decimal(str(ratio))) if import_vat else None,
        })
    
    await db.commit()
    
    return {
        "master_invoice": target_master.invoice_no,
        "allocation_method": allocation_method,
        "total_boxes": total_boxes,
        "allocated": allocated,
    }


@router.post("/batch-import", status_code=status.HTTP_201_CREATED)
async def batch_import_invoices(
    records: List[dict],
    db: AsyncSession = Depends(get_db),
):
    """批量导入进口单证
    
    每行数据需要包含: invoice_no, invoice_date, kill_date, processing_plant, fish_farm, exporter
    自动查找或创建加工厂/渔场/出口商
    返回: {created: 新增数, errors: 错误列表, items: 发票列表}
    """
    from app.services.company_service import CompanyService
    from app.models import CompanyType
    from datetime import datetime
    
    created_count = 0
    result_items = []
    errors = []
    
    for idx, record in enumerate(records):
        try:
            invoice_no = record.get("invoice_no", "").strip()
            if not invoice_no:
                errors.append({"row": idx + 1, "error": "发票号不能为空"})
                continue
            
            # 检查是否已存在
            existing = await InvoiceService.get_by_invoice_no(db, invoice_no)
            if existing:
                errors.append({"row": idx + 1, "error": f"发票号 {invoice_no} 已存在"})
                continue
            
            # 解析日期
            invoice_date = record.get("invoice_date", "").strip()
            kill_date = record.get("kill_date", "").strip()
            
            def parse_date(d):
                if not d:
                    return None
                try:
                    return datetime.strptime(d, "%Y-%m-%d").date()
                except ValueError:
                    try:
                        return datetime.strptime(d, "%Y/%m/%d").date()
                    except ValueError:
                        return None
            
            invoice_date_parsed = parse_date(invoice_date)
            kill_date_parsed = parse_date(kill_date)
            
            if not invoice_date_parsed:
                errors.append({"row": idx + 1, "error": "发票日期格式错误"})
                continue
            
            # 查找或创建加工厂
            pp_name = record.get("processing_plant", "").strip()
            pp_id = None
            if pp_name:
                pp = await CompanyService.get_or_create_company(db, name=pp_name, type=CompanyType.PROCESSING_PLANT)
                pp_id = pp.id
            
            # 查找或创建渔场
            ff_name = record.get("fish_farm", "").strip()
            ff_id = None
            if ff_name:
                ff = await CompanyService.get_or_create_company(db, name=ff_name, type=CompanyType.FISH_FARM)
                ff_id = ff.id
            
            # 查找或创建出口商
            ex_name = record.get("exporter", "").strip()
            ex_id = None
            if ex_name:
                ex = await CompanyService.get_or_create_company(db, name=ex_name, type=CompanyType.EXPORTER)
                ex_id = ex.id
            
            # 创建发票
            invoice_data = {
                "invoice_no": invoice_no,
                "invoice_date": invoice_date_parsed,
                "kill_date": kill_date_parsed,
                "processing_plant_id": pp_id,
                "fish_farm_id": ff_id,
                "exporter_id": ex_id,
                "total_amount_usd": Decimal(str(record.get("total_amount_usd", 0))),
                "total_boxes": int(record.get("total_boxes", 0)),
                "total_weight_kg": Decimal(str(record.get("total_weight_kg", 0))),
                "awb_no": record.get("awb_no", ""),
                "gross_weight_kg": Decimal(str(record.get("gross_weight_kg", 0))),
                "eta": record.get("eta", ""),
                "departure_date": parse_date(record.get("departure_date", "").strip()),
                "flight_info": record.get("flight_info", ""),
                "origin_certificate": record.get("origin_certificate", ""),
                "inspection_certificate": record.get("inspection_certificate", ""),
                "customs_status": "pending_customs",
                "exchange_status": "not_exchanged",
                "notes": record.get("notes", ""),
            }
            
            invoice = await InvoiceService.create(db, invoice_data)
            created_count += 1
            result_items.append(invoice)
            
        except Exception as e:
            errors.append({"row": idx + 1, "error": str(e)})
    
    return {
        "created": created_count,
        "errors": errors,
        "items": result_items,
    }

