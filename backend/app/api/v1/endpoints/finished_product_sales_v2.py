"""成品销售 API V2

- 旧版 /finished-product-sales/with-items 等扩展端点（以销定采）
- 新版 /finished-product-sales-v2 CRUD + 收款 + 导出
- 产品单位换算 /product-unit-conversions
"""
from csv import writer
from datetime import date
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Product
from app.models.finished_product_v2 import SaleItemType
from app.models.warehouse import ProductUnitConversion
from app.schemas.finished_product_v2 import (
    FinishedProductSaleItemResponse,
    FinishedProductSaleV2Create,
    FinishedProductSaleV2ListResponse,
    FinishedProductSaleV2ReceiptCreate,
    FinishedProductSaleV2Response,
    FinishedProductSaleV2Update,
    FinishedProductSaleWithItemsCreate,
    SlaughterDateOption,
)
from app.schemas.warehouse_v2 import (
    ProductUnitConversionCreate,
    ProductUnitConversionListResponse,
    ProductUnitConversionResponse,
)
from app.services.daily_slaughter_service import DailySlaughterService
from app.services.finished_product_sale_v2 import (
    FinishedProductSaleServiceV2,
    FinishedProductSaleV2Service,
)

# 保持旧版 V2 扩展端点（以销定采/宰杀关联）
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


@router.get("/options/slaughter-dates", response_model=list[SlaughterDateOption])
async def get_available_slaughter_dates(
    min_available_kg: Decimal | None = Query(Decimal("0")),
    db: AsyncSession = Depends(get_db),
):
    """获取可供销售的宰杀日期列表"""
    dates = await DailySlaughterService.get_available_slaughter_dates(db, min_available_kg)
    return [SlaughterDateOption(**d) for d in dates]


@router.get("/{sale_id}/items", response_model=list[FinishedProductSaleItemResponse])
async def get_sale_items(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取销售子项列表"""
    items = await FinishedProductSaleServiceV2.get_sale_items(db, sale_id)
    return [FinishedProductSaleItemResponse.model_validate(i) for i in items]


# 新版 FinishedProductSaleV2 模型端点
v2_router = APIRouter()


@v2_router.get("/", response_model=FinishedProductSaleV2ListResponse)
async def list_finished_product_sales_v2(
    sale_type: str | None = Query(None, description="销售类型"),
    customer: str | None = Query(None, description="客户名称"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """成品销售 V2 列表"""
    items, total = await FinishedProductSaleV2Service.list_sales(
        db=db,
        sale_type=sale_type,
        customer=customer,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return FinishedProductSaleV2ListResponse(
        total=total,
        items=[FinishedProductSaleV2Response.model_validate(i) for i in items],
        skip=skip,
        limit=limit,
    )


@v2_router.get("/export", response_class=PlainTextResponse)
async def export_finished_product_sales_v2(
    sale_type: str | None = Query(None, description="销售类型"),
    customer: str | None = Query(None, description="客户名称"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
):
    """导出成品销售 V2 列表为 CSV"""
    items, _ = await FinishedProductSaleV2Service.list_sales(
        db=db,
        sale_type=sale_type,
        customer=customer,
        start_date=start_date,
        end_date=end_date,
        skip=0,
        limit=10000,
    )

    output = StringIO()
    csv_writer = writer(output)
    csv_writer.writerow([
        "销售单号", "销售类型", "客户", "业务员", "产品名称", "数量", "重量",
        "单价", "总金额", "销售日期", "折扣", "扫码费", "抹零", "售后调整",
        "佣金", "余额调整", "应付金额", "已付金额", "是否付清", "备注", "状态",
        "批次号", "加工厂", "收货地址", "物流信息",
    ])

    for sale in items:
        csv_writer.writerow([
            sale.sale_no or "",
            sale.sale_type or "",
            sale.customer or "",
            sale.salesperson or "",
            sale.product_name or "",
            sale.quantity or 0,
            sale.weight or 0,
            sale.unit_price or 0,
            sale.total_amount or 0,
            sale.sale_date.isoformat() if sale.sale_date else "",
            sale.discount or 0,
            sale.scan_fee or 0,
            sale.rounding or 0,
            sale.after_sales_adjustment or 0,
            sale.commission or 0,
            sale.balance_adjustment or 0,
            sale.net_amount or 0,
            sale.paid_amount or 0,
            sale.paid or 0,
            sale.remark or "",
            sale.status or "",
            sale.batch_no or "",
            sale.factory or "",
            sale.delivery_address or "",
            sale.logistics_info or "",
        ])

    content = output.getvalue()
    output.close()

    headers = {
        "Content-Disposition": "attachment; filename=finished_product_sales_v2.csv"
    }
    return PlainTextResponse(content, media_type="text/csv; charset=utf-8", headers=headers)


@v2_router.get("/{sale_id}", response_model=FinishedProductSaleV2Response)
async def get_finished_product_sale_v2(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """成品销售 V2 详情"""
    sale = await FinishedProductSaleV2Service.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    return FinishedProductSaleV2Response.model_validate(sale)


@v2_router.post("/", response_model=FinishedProductSaleV2Response, status_code=status.HTTP_201_CREATED)
async def create_finished_product_sale_v2(
    data: FinishedProductSaleV2Create,
    db: AsyncSession = Depends(get_db),
):
    """创建成品销售 V2"""
    sale = await FinishedProductSaleV2Service.create_sale(db, data.model_dump())
    return FinishedProductSaleV2Response.model_validate(sale)


@v2_router.put("/{sale_id}", response_model=FinishedProductSaleV2Response)
async def update_finished_product_sale_v2(
    sale_id: int,
    data: FinishedProductSaleV2Update,
    db: AsyncSession = Depends(get_db),
):
    """更新成品销售 V2"""
    sale = await FinishedProductSaleV2Service.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    updated = await FinishedProductSaleV2Service.update_sale(db, sale, data.model_dump(exclude_unset=True))
    return FinishedProductSaleV2Response.model_validate(updated)


@v2_router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finished_product_sale_v2(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除成品销售 V2"""
    sale = await FinishedProductSaleV2Service.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    await FinishedProductSaleV2Service.delete_sale(db, sale)
    return None


@v2_router.post("/{sale_id}/receipts", response_model=FinishedProductSaleV2Response, status_code=status.HTTP_201_CREATED)
async def create_finished_product_sale_v2_receipt(
    sale_id: int,
    data: FinishedProductSaleV2ReceiptCreate,
    db: AsyncSession = Depends(get_db),
):
    """添加成品销售 V2 收款记录"""
    sale = await FinishedProductSaleV2Service.get_by_id(db, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="销售记录不存在")
    await FinishedProductSaleV2Service.add_receipt(db, sale, data.model_dump())
    db.expire(sale)
    refreshed = await FinishedProductSaleV2Service.get_by_id(db, sale_id)
    return FinishedProductSaleV2Response.model_validate(refreshed)


@v2_router.delete("/{sale_id}/receipts/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finished_product_sale_v2_receipt(
    sale_id: int,
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除成品销售 V2 收款记录"""
    await FinishedProductSaleV2Service.delete_receipt(db, receipt_id)
    return None


# 产品单位换算 CRUD 路由
conversion_router = APIRouter()


@conversion_router.get("/", response_model=ProductUnitConversionListResponse)
async def list_product_unit_conversions(
    product_id: int | None = Query(None, description="产品ID"),
    product_name: str | None = Query(None, description="产品名称（当 product_id 为空时尝试按名称查找）"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """查询产品单位换算规则"""
    query = select(ProductUnitConversion)
    if product_id:
        query = query.where(ProductUnitConversion.product_id == product_id)
    elif product_name:
        result = await db.execute(select(Product.id).where(Product.name == product_name).limit(1))
        resolved_id = result.scalar_one_or_none()
        if resolved_id:
            query = query.where(ProductUnitConversion.product_id == resolved_id)
        else:
            query = query.where(ProductUnitConversion.id < 0)

    count_query = select(func.count(ProductUnitConversion.id)).select_from(query.subquery())
    query = query.order_by(ProductUnitConversion.from_unit, ProductUnitConversion.to_unit)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return ProductUnitConversionListResponse(
        total=total,
        items=[ProductUnitConversionResponse.model_validate(i) for i in items],
        skip=skip,
        limit=limit,
    )


@conversion_router.post("/", response_model=ProductUnitConversionResponse, status_code=status.HTTP_201_CREATED)
async def create_product_unit_conversion(
    data: ProductUnitConversionCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建产品单位换算规则"""
    conversion = ProductUnitConversion(**data.model_dump())
    db.add(conversion)
    await db.commit()
    await db.refresh(conversion)
    return ProductUnitConversionResponse.model_validate(conversion)


@conversion_router.get("/{conversion_id}", response_model=ProductUnitConversionResponse)
async def get_product_unit_conversion(
    conversion_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单位换算规则详情"""
    conversion = await db.get(ProductUnitConversion, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="换算规则不存在")
    return ProductUnitConversionResponse.model_validate(conversion)


@conversion_router.put("/{conversion_id}", response_model=ProductUnitConversionResponse)
async def update_product_unit_conversion(
    conversion_id: int,
    data: ProductUnitConversionCreate,
    db: AsyncSession = Depends(get_db),
):
    """更新单位换算规则"""
    conversion = await db.get(ProductUnitConversion, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="换算规则不存在")
    for field, value in data.model_dump().items():
        setattr(conversion, field, value)
    await db.commit()
    await db.refresh(conversion)
    return ProductUnitConversionResponse.model_validate(conversion)


@conversion_router.delete("/{conversion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_unit_conversion(
    conversion_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除单位换算规则"""
    conversion = await db.get(ProductUnitConversion, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="换算规则不存在")
    await db.delete(conversion)
    await db.commit()
    return None
