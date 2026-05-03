from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import (
    SalesStatus,
    FinishedProductSale,
    FinishedProductAftersales,
    Company,
    Product,
    ProductCategory,
    User,
)
from app.schemas.finished_product_sales import (
    FinishedProductSaleCreate,
    FinishedProductSaleUpdate,
    FinishedProductSaleResponse,
    FinishedProductSaleListResponse,
    FinishedProductSaleSummary,
    FinishedProductReceiptCreate,
    FinishedProductReceiptResponse,
    FinishedProductAftersalesCreate,
    FinishedProductAftersalesUpdate,
    FinishedProductAftersalesResponse,
)
from app.services.finished_product_sale_service import FinishedProductSaleService

router = APIRouter()


async def _build_sale_response(
    db: AsyncSession, sale: FinishedProductSale
) -> FinishedProductSaleResponse:
    """构建成品销售响应（含关联信息）"""
    customer_name = None
    product_name = None
    product_spec = None
    salesperson_name = None

    if sale.customer_id:
        r = await db.execute(select(Company.name).where(Company.id == sale.customer_id))
        customer_name = r.scalar()
    if sale.product_id:
        r = await db.execute(
            select(Product.name, Product.spec).where(Product.id == sale.product_id)
        )
        product_row = r.one_or_none()
        if product_row:
            product_name = product_row[0]
            product_spec = product_row[1]
    if sale.salesperson_id:
        r = await db.execute(
            select(User.full_name).where(User.id == sale.salesperson_id)
        )
        salesperson_name = r.scalar()

    receipts = [
        FinishedProductReceiptResponse.model_validate(r) for r in (sale.receipts or [])
    ]
    aftersales = [
        FinishedProductAftersalesResponse.model_validate(a)
        for a in (sale.aftersales_records or [])
    ]

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
        receipts=receipts,
        aftersales=aftersales,
    )


@router.get("/summary", response_model=FinishedProductSaleSummary)
async def get_finished_product_sales_summary(
    db: AsyncSession = Depends(get_db),
):
    """成品销售汇总统计"""
    summary = await FinishedProductSaleService.get_summary(db)
    return FinishedProductSaleSummary(**summary)


# ==================== 成品销售 CRUD ====================


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
        db=db,
        customer_id=customer_id,
        product_id=product_id,
        status=status,
        skip=skip,
        limit=limit,
    )
    result_items = []
    for sale in items:
        result_items.append(await _build_sale_response(db, sale))
    return FinishedProductSaleListResponse(
        total=total, items=result_items, skip=skip, limit=limit
    )


@router.post(
    "/", response_model=FinishedProductSaleResponse, status_code=status.HTTP_201_CREATED
)
async def create_finished_product_sale(
    data: FinishedProductSaleCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建成品销售"""
    # 信用额度校验
    is_allowed, message = await FinishedProductSaleService.check_customer_credit(
        db, data.customer_id, data.net_amount
    )
    if not is_allowed:
        raise HTTPException(status_code=400, detail=message)

    sale = await FinishedProductSaleService.create_sale(db, data.model_dump())
    return await _build_sale_response(db, sale)


@router.get("/{sale_id}", response_model=FinishedProductSaleResponse)
async def get_finished_product_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """成品销售详情"""
    sale = await FinishedProductSaleService.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在"
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在"
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在"
        )
    await FinishedProductSaleService.delete_sale(db, sale)
    return None


# ==================== 收款记录 ====================


@router.get(
    "/{sale_id}/receipts", response_model=List[FinishedProductReceiptResponse]
)
async def list_finished_product_receipts(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """成品销售收款记录列表"""
    sale = await FinishedProductSaleService.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在"
        )
    return [
        FinishedProductReceiptResponse.model_validate(r) for r in (sale.receipts or [])
    ]


@router.post(
    "/{sale_id}/receipts",
    response_model=FinishedProductReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_finished_product_receipt(
    sale_id: int,
    data: FinishedProductReceiptCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建成品销售收款记录"""
    receipt = await FinishedProductSaleService.add_receipt(db, sale_id, data.model_dump())
    return FinishedProductReceiptResponse.model_validate(receipt)


@router.delete(
    "/{sale_id}/receipts/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_finished_product_receipt(
    sale_id: int,
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除成品销售收款记录"""
    await FinishedProductSaleService.delete_receipt(db, receipt_id)
    return None


# ==================== 售后记录 ====================


@router.get(
    "/{sale_id}/aftersales", response_model=List[FinishedProductAftersalesResponse]
)
async def list_finished_product_aftersales(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """成品销售售后记录列表"""
    sale = await FinishedProductSaleService.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在"
        )
    return [
        FinishedProductAftersalesResponse.model_validate(a)
        for a in (sale.aftersales_records or [])
    ]


@router.post(
    "/{sale_id}/aftersales",
    response_model=FinishedProductAftersalesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_finished_product_aftersales(
    sale_id: int,
    data: FinishedProductAftersalesCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建成品销售售后记录"""
    record = await FinishedProductSaleService.add_aftersales(
        db, sale_id, data.model_dump()
    )
    return FinishedProductAftersalesResponse.model_validate(record)


@router.put(
    "/{sale_id}/aftersales/{record_id}",
    response_model=FinishedProductAftersalesResponse,
)
async def update_finished_product_aftersales(
    sale_id: int,
    record_id: int,
    data: FinishedProductAftersalesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新成品销售售后记录"""
    result = await db.execute(
        select(FinishedProductAftersales).where(
            FinishedProductAftersales.id == record_id,
            FinishedProductAftersales.sale_id == sale_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="售后记录不存在"
        )
    update_data = data.model_dump(exclude_unset=True)
    updated = await FinishedProductSaleService.update_aftersales(
        db, record, update_data
    )
    return FinishedProductAftersalesResponse.model_validate(updated)


@router.delete(
    "/{sale_id}/aftersales/{record_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_finished_product_aftersales(
    sale_id: int,
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除成品销售售后记录"""
    await FinishedProductSaleService.delete_aftersales(db, record_id)
    return None


# ==================== 批量导入 ====================


@router.post("/batch-import", status_code=status.HTTP_201_CREATED)
async def batch_import_finished_product_sales(
    records: List[dict],
    db: AsyncSession = Depends(get_db),
):
    """批量导入成品销售记录

    每行数据需要包含: customer_name, product_name, sale_date, quantity, unit_price
    自动查找或创建客户，自动查找产品，自动计算金额
    返回: {created: 新增数, errors: 错误列表, items: 销售列表}
    """
    from app.services.company_service import CompanyService

    created_count = 0
    result_items = []
    errors = []

    for idx, record in enumerate(records):
        try:
            customer_name = record.get("customer_name", "").strip()
            product_name = record.get("product_name", "").strip()

            if not customer_name:
                errors.append({"row": idx + 1, "error": "客户名称不能为空"})
                continue
            if not product_name:
                errors.append({"row": idx + 1, "error": "产品名称不能为空"})
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

            # 查找产品（按名称匹配）
            product_id = None
            result = await db.execute(
                select(Product)
                .where(Product.name == product_name)
                .where(Product.category == ProductCategory.FINISHED_PRODUCT)
                .limit(1)
            )
            product = result.scalar_one_or_none()
            if product:
                product_id = product.id
            else:
                errors.append(
                    {
                        "row": idx + 1,
                        "error": f"未找到产品: {product_name}",
                    }
                )
                continue

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

            # 解析数量和单价
            quantity = int(record.get("quantity", 0))
            unit_price = Decimal(str(record.get("unit_price", 0)))
            scan_fee = Decimal(str(record.get("scan_fee", 0)))
            discount = Decimal(str(record.get("discount", 0)))
            commission = Decimal(str(record.get("commission", 0)))

            if quantity <= 0:
                errors.append({"row": idx + 1, "error": "数量必须大于0"})
                continue
            if unit_price <= 0:
                errors.append({"row": idx + 1, "error": "单价必须大于0"})
                continue

            # 计算金额
            gross_amount = (Decimal(quantity) * unit_price).quantize(Decimal("0.01"))
            net_amount = gross_amount - scan_fee - discount - commission

            # 信用额度校验
            is_allowed, message = await FinishedProductSaleService.check_customer_credit(
                db, customer.id, net_amount
            )
            if not is_allowed:
                errors.append({"row": idx + 1, "error": message})
                continue

            # 创建销售记录
            sale_data = {
                "customer_id": customer.id,
                "product_id": product_id,
                "sale_date": sale_date,
                "quantity": quantity,
                "unit_price": unit_price,
                "gross_amount": gross_amount,
                "scan_fee": scan_fee,
                "discount": discount,
                "commission": commission,
                "net_amount": net_amount,
                "paid_amount": Decimal("0"),
                "status": "pending",
                "notes": record.get("notes", ""),
            }

            sale = await FinishedProductSaleService.create_sale(db, sale_data)
            created_count += 1
            result_items.append(await _build_sale_response(db, sale))

        except Exception as e:
            errors.append({"row": idx + 1, "error": str(e)})

    return {
        "created": created_count,
        "errors": errors,
        "items": result_items,
    }
