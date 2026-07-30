from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    BankAccount,
    Batch,
    BatchInvoice,
    Company,
    FinishedProductSaleV2,
    FinishedSaleProductV2,
    ImportInvoice,
    InvoiceProduct,
    WholeFishSale,
    WholeFishSaleItem,
)
from app.models.system import SystemConfig
from app.models.user import User


class PrintService:
    """销售单打印数据统一服务"""

    @staticmethod
    async def get_sale_print_data(
        db: AsyncSession, sale_type: str, sale_id: int
    ) -> dict[str, Any]:
        """根据销售类型和 ID 统一组装打印数据"""
        receipt_accounts = await PrintService._get_receipt_accounts(db)

        if sale_type == "whole_fish":
            return await PrintService._build_whole_fish_data(
                db, sale_id, receipt_accounts
            )
        if sale_type == "finished_product_v2":
            return await PrintService._build_finished_v2_data(
                db, sale_id, receipt_accounts
            )

        raise HTTPException(status_code=400, detail=f"不支持的打印类型: {sale_type}")

    @staticmethod
    async def _get_receipt_accounts(db: AsyncSession) -> list[dict[str, str]]:
        """读取系统默认收款公司的所有银行账户信息"""
        result = await db.execute(
            select(SystemConfig).where(
                SystemConfig.config_key == "default_receipt_company_id"
            )
        )
        cfg = result.scalar_one_or_none()
        if not cfg or not cfg.config_value:
            return []
        try:
            company_id = int(cfg.config_value)
        except ValueError:
            return []

        accounts = await db.execute(
            select(BankAccount)
            .where(BankAccount.company_id == company_id, BankAccount.is_active)
            .order_by(BankAccount.id)
        )
        return [
            {
                "account_name": acc.account_name,
                "bank_name": acc.bank_name or "",
                "account_number": acc.account_number or "",
                "currency": acc.currency or "CNY",
                "notes": acc.notes or "",
            }
            for acc in accounts.scalars().all()
        ]

    @staticmethod
    async def _build_whole_fish_data(
        db: AsyncSession, sale_id: int, receipt_accounts: list[dict[str, str]]
    ) -> dict[str, Any]:
        """进口销售（整鱼销售）打印数据"""
        result = await db.execute(
            select(WholeFishSale)
            .options(
                selectinload(WholeFishSale.items),
            )
            .where(WholeFishSale.id == sale_id)
        )
        sale = result.scalar_one_or_none()
        if not sale:
            raise HTTPException(status_code=404, detail="销售单不存在")

        # 客户
        customer = await db.get(Company, sale.customer_id)
        customer_name = customer.name if customer else "-"

        # 业务员
        salesperson = await db.get(User, sale.salesperson_id)
        salesperson_name = salesperson.full_name or salesperson.username if salesperson else "-"

        # 批次与关联进口发票
        batch = await db.get(Batch, sale.batch_id)
        invoice_products: list[InvoiceProduct] = []
        processing_plant: Company | None = None
        kill_date: date | None = None
        if batch:
            bi_result = await db.execute(
                select(BatchInvoice)
                .where(BatchInvoice.batch_id == batch.id)
                .order_by(BatchInvoice.sort_order)
            )
            batch_invoices = bi_result.scalars().all()
            if batch_invoices:
                invoice = await db.get(ImportInvoice, batch_invoices[0].invoice_id)
                if invoice:
                    kill_date = invoice.kill_date
                    if invoice.processing_plant_id:
                        processing_plant = await db.get(
                            Company, invoice.processing_plant_id
                        )
                    # 读取该发票下的产品明细用于匹配实际产品名
                    ip_result = await db.execute(
                        select(InvoiceProduct).where(
                            InvoiceProduct.invoice_id == invoice.id
                        )
                    )
                    invoice_products = ip_result.scalars().all()

        factory_name = processing_plant.code if processing_plant else (
            processing_plant.name if processing_plant else "-"
        )
        slaughter_date = PrintService._format_mdy(kill_date) if kill_date else "-"

        # 构建明细
        items: list[dict[str, Any]] = []
        for idx, item in enumerate(sale.items or [], start=1):
            product_name = PrintService._match_product_name(
                item.spec, invoice_products
            )
            items.append(
                {
                    "seq": idx,
                    "product": product_name,
                    "spec": item.spec or "-",
                    "factory": factory_name,
                    "slaughter_date": slaughter_date,
                    "batch": batch.batch_code if batch else "-",
                    "quantity": int(item.box_count or 0),
                    "quantity_unit": "箱",
                    "weight": str(item.weight_kg) if item.weight_kg else None,
                    "weight_unit": "kg",
                    "unit_price": float(item.unit_price or 0),
                    "price_unit": "元/kg",
                    "amount": float(item.amount or 0),
                    "remark": item.notes or "",
                }
            )

        return PrintService._build_response(
            sale_type="whole_fish",
            sale_type_label="整鱼",
            sale=sale,
            customer_name=customer_name,
            salesperson_name=salesperson_name,
            items=items,
            receipt_accounts=receipt_accounts,
        )

    @staticmethod
    async def _build_finished_v2_data(
        db: AsyncSession, sale_id: int, receipt_accounts: list[dict[str, str]]
    ) -> dict[str, Any]:
        """以销定采 / 预包装 / 海鲜物料（finished_product_sales_v2）打印数据"""
        result = await db.execute(
            select(FinishedProductSaleV2)
            .options(selectinload(FinishedProductSaleV2.products))
            .where(FinishedProductSaleV2.id == sale_id)
        )
        sale = result.scalar_one_or_none()
        if not sale:
            raise HTTPException(status_code=404, detail="销售单不存在")

        customer_name = sale.customer or "-"
        salesperson_name = sale.salesperson or "-"

        # 判断单据类型标签
        # 默认以 sale_type 为准；当 sale_type='finished_product' 时，
        # 如果明细中存在按单位售卖的（无重量、有 sale_unit），则标记为海鲜物料
        sale_type_label = "整鱼"
        if sale.sale_type == "finished_product":
            sale_type_label = "预包装"
            for product in sale.products or []:
                if product.sale_unit and not product.weight_kg:
                    sale_type_label = "海鲜物料"
                    break

        items: list[dict[str, Any]] = []
        for idx, product in enumerate(sale.products or [], start=1):
            if sale.sale_type == "whole_fish":
                # 以销定采：结构同整鱼，加工厂/宰杀日期取自产品明细
                items.append(
                    {
                        "seq": idx,
                        "product": product.product_name or "-",
                        "spec": product.product_spec or "-",
                        "factory": product.factory or sale.factory or "-",
                        "slaughter_date": PrintService._format_mdy(
                            product.slaughter_date
                        ),
                        "batch": product.batch or sale.batch_no or "-",
                        "quantity": int(product.box_count or 0),
                        "quantity_unit": "箱",
                        "weight": str(product.weight_kg) if product.weight_kg else None,
                        "weight_unit": "kg",
                        "unit_price": float(product.unit_price or 0),
                        "price_unit": "元/kg",
                        "amount": float(product.total_amount or 0),
                        "remark": "",
                    }
                )
            elif sale_type_label == "海鲜物料":
                # 海鲜物料：按单位售卖，无加工厂、宰杀日期、重量
                items.append(
                    {
                        "seq": idx,
                        "product": product.product_name or "-",
                        "spec": product.product_spec or "-",
                        "factory": None,
                        "slaughter_date": None,
                        "batch": None,
                        "quantity": float(product.base_quantity or 0),
                        "quantity_unit": product.sale_unit or "件",
                        "weight": None,
                        "weight_unit": None,
                        "unit_price": float(product.unit_price or 0),
                        "price_unit": f"元/{product.sale_unit or '件'}",
                        "amount": float(product.total_amount or 0),
                        "remark": "",
                    }
                )
            else:
                # 预包装：按重量，份数
                weight_display = None
                if product.weight_kg and product.weight_kg > 0:
                    weight_display = str(product.weight_kg)
                items.append(
                    {
                        "seq": idx,
                        "product": product.product_name or "-",
                        "spec": product.product_spec or "-",
                        "factory": None,
                        "slaughter_date": None,
                        "batch": None,
                        "quantity": int(product.box_count or 0),
                        "quantity_unit": "份",
                        "weight": weight_display,
                        "weight_unit": "kg" if weight_display else None,
                        "unit_price": float(product.unit_price or 0),
                        "price_unit": "元/份",
                        "amount": float(product.total_amount or 0),
                        "remark": "",
                    }
                )

        return PrintService._build_response(
            sale_type=sale.sale_type or "finished_product",
            sale_type_label=sale_type_label,
            sale=sale,
            customer_name=customer_name,
            salesperson_name=salesperson_name,
            items=items,
            receipt_accounts=receipt_accounts,
        )

    @staticmethod
    def _build_response(
        *,
        sale_type: str,
        sale_type_label: str,
        sale: Any,
        customer_name: str,
        salesperson_name: str,
        items: list[dict[str, Any]],
        receipt_accounts: list[dict[str, str]],
    ) -> dict[str, Any]:
        """组装统一返回结构"""
        total_amount = sum((Decimal(str(i["amount"])) for i in items), Decimal("0"))
        total_quantity = sum(i["quantity"] for i in items)
        total_weight = sum(
            (Decimal(i["weight"]) for i in items if i.get("weight")),
            Decimal("0"),
        )

        # 兼容不同模型的金额字段
        gross_amount = getattr(sale, "gross_amount", None) or getattr(
            sale, "total_amount", None
        ) or total_amount
        net_amount = getattr(sale, "net_amount", None) or getattr(
            sale, "actual_amount", None
        ) or gross_amount
        paid_amount = getattr(sale, "paid_amount", Decimal("0")) or Decimal("0")

        sale_date = getattr(sale, "sale_date", None)
        sale_no = getattr(sale, "sale_no", None)
        remark = getattr(sale, "notes", None) or getattr(sale, "remark", None) or ""

        return {
            "sale_type": sale_type,
            "sale_type_label": sale_type_label,
            "sale_no": sale_no or "-",
            "sale_date": str(sale_date) if sale_date else "-",
            "customer": customer_name,
            "salesperson": salesperson_name,
            "items": items,
            "summary": {
                "total_quantity": total_quantity,
                "total_weight": str(total_weight) if total_weight else None,
                "total_amount": float(total_amount),
                "gross_amount": float(gross_amount),
                "net_amount": float(net_amount),
                "paid_amount": float(paid_amount),
                "unpaid_amount": float(Decimal(net_amount) - Decimal(paid_amount)),
            },
            "receipt_accounts": receipt_accounts,
            "remark": remark or "",
        }

    @staticmethod
    def _format_mdy(d: date | None) -> str:
        """日期格式化为 MM-DD（用于宰杀日期）"""
        if not d:
            return "-"
        return f"{d.month:02d}{d.day:02d}"

    @staticmethod
    def _match_product_name(spec: str | None, products: list[InvoiceProduct]) -> str:
        """根据规格匹配进口发票产品名"""
        if not spec:
            if products:
                return products[0].product_name
            return "三文鱼"

        for p in products:
            if p.product_spec == spec:
                return p.product_name

        if products:
            return products[0].product_name
        return "三文鱼"
