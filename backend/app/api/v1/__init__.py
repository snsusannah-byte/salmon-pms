from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit,
    auth,
    batches,
    brands,
    companies,
    daily_slaughter,
    dashboard,
    finance,
    finance_v4_migration,
    finished_product_sales,
    finished_product_sales_v2,
    finished_products,
    invoices,
    loss_records,
    material_categories,
    material_purchases,
    materials,
    notifications,
    print as print_endpoint,
    products,
    purchase_inbound,
    purchase_orders,
    purchase_returns,
    reports,
    returns,
    sales,
    sales_batch_collect,
    salespersons,
    settings,
    traceability,
    warehouse,
    warehouse_v2,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(companies.router, prefix="/companies", tags=["主体管理"])
api_router.include_router(products.router, prefix="/products", tags=["产品管理"])
api_router.include_router(brands.router, prefix="/brands", tags=["品牌管理"])
api_router.include_router(finished_products.router, prefix="/finished-products", tags=["成品定义"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["进口单证"])
api_router.include_router(batches.router, prefix="/batches", tags=["批次管理"])
api_router.include_router(sales.router, prefix="/sales", tags=["整鱼销售"])
api_router.include_router(sales_batch_collect.router, prefix="/sales/whole-fish", tags=["整鱼销售"])
api_router.include_router(finished_product_sales.router, prefix="/finished-product-sales", tags=["成品销售"])
api_router.include_router(finance.router, prefix="/finance", tags=["财务管理"])
api_router.include_router(reports.router, prefix="/reports", tags=["报表中心"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["数据看板"])
api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
api_router.include_router(audit.router, prefix="/audit", tags=["审计日志"])
api_router.include_router(salespersons.router, prefix="/salespersons", tags=["业务员管理"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知中心"])

# V3新增路由
api_router.include_router(daily_slaughter.router, prefix="/daily-slaughter", tags=["daily-slaughter"])
api_router.include_router(warehouse.router, prefix="/warehouse", tags=["warehouse"])
api_router.include_router(warehouse_v2.router, prefix="/warehouse-v2", tags=["warehouse-v2"])
api_router.include_router(loss_records.router, prefix="/loss-records", tags=["loss-records"])
api_router.include_router(finished_product_sales_v2.router, prefix="/finished-product-sales", tags=["finished-product-sales-v2"])
api_router.include_router(finished_product_sales_v2.v2_router, prefix="/finished-product-sales-v2", tags=["finished-product-sales-v2"])
api_router.include_router(finished_product_sales_v2.conversion_router, prefix="/product-unit-conversions", tags=["product-unit-conversions"])
api_router.include_router(print_endpoint.router, prefix="/print/sales", tags=["打印"])
api_router.include_router(materials.router, prefix="/materials", tags=["物料管理"])
api_router.include_router(material_categories.router, prefix="/material-categories", tags=["物料分类"])
api_router.include_router(material_purchases.router, prefix="/material-purchases", tags=["物料采购"])
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["采购入库"])
api_router.include_router(traceability.router, prefix="/traceability", tags=["追溯系统"])
api_router.include_router(returns.router, prefix="/returns", tags=["退货管理"])

api_router.include_router(purchase_inbound.router, tags=["采购入库"])
api_router.include_router(purchase_returns.router, prefix="/purchase-returns", tags=["采购售后"])
api_router.include_router(finance_v4_migration.router, prefix="/v4", tags=["国内采购与成品销售"])
