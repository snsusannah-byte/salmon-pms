from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    companies,
    products,
    invoices,
    batches,
    sales,
    finished_product_sales,
    finance,
    reports,
    dashboard,
    settings,
    salespersons,
    notifications,
    daily_slaughter,
    warehouse,
    loss_records,
    finished_product_sales_v2,
    materials,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(companies.router, prefix="/companies", tags=["主体管理"])
api_router.include_router(products.router, prefix="/products", tags=["产品管理"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["进口单证"])
api_router.include_router(batches.router, prefix="/batches", tags=["批次管理"])
api_router.include_router(sales.router, prefix="/sales", tags=["整鱼销售"])
api_router.include_router(finished_product_sales.router, prefix="/finished-product-sales", tags=["成品销售"])
api_router.include_router(finance.router, prefix="/finance", tags=["财务管理"])
api_router.include_router(reports.router, prefix="/reports", tags=["报表中心"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["数据看板"])
api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
api_router.include_router(salespersons.router, prefix="/salespersons", tags=["业务员管理"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知中心"])

# V3新增路由
api_router.include_router(daily_slaughter.router, prefix="/daily-slaughter", tags=["daily-slaughter"])
api_router.include_router(warehouse.router, prefix="/warehouse", tags=["warehouse"])
api_router.include_router(loss_records.router, prefix="/loss-records", tags=["loss-records"])
api_router.include_router(finished_product_sales_v2.router, prefix="/finished-product-sales", tags=["finished-product-sales-v2"])
api_router.include_router(materials.router, prefix="/materials", tags=["物料管理"])
