import asyncio
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models import ImportInvoice, InvoiceProduct, Notification
from app.core.database import AsyncSessionLocal

class InvoiceNotificationService:
    """进口单证通知服务"""
    
    @staticmethod
    def generate_arrival_notification(invoice: ImportInvoice, products: list[InvoiceProduct], processing_plant_display: str = None) -> str:
        """生成预计到货通知（纯文本，微信适用）"""
        # 从 ETA 获取到货日期时间（年月日时分）
        if invoice.eta:
            if isinstance(invoice.eta, datetime):
                arrival_datetime = invoice.eta.strftime("%Y-%m-%d %H:%M")
            elif isinstance(invoice.eta, str):
                try:
                    dt = datetime.fromisoformat(invoice.eta.replace("Z", "+00:00"))
                    arrival_datetime = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    arrival_datetime = invoice.eta
            else:
                arrival_datetime = str(invoice.eta)
        else:
            arrival_datetime = "-"
        
        lines = [
            "【预计到货通知】",
            "",
            f"合同编号：{invoice.invoice_no}",
            f"空运单号：{invoice.awb_no or '-'}",
            "",
            f"到货日期：{arrival_datetime}",
            f"宰杀日期：{invoice.kill_date or '-'}",
            f"加工厂：{processing_plant_display or '-'}",
            "",
            "规格箱数：",
        ]
        
        total_boxes = 0
        for p in products:
            lines.append(f"{p.product_spec}：{p.box_count}箱")
            total_boxes += p.box_count or 0
        
        lines.append(f"合计：{total_boxes}箱")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_tax_notification(invoice: ImportInvoice) -> str:
        """生成预计税金通知（纯文本，只给结果）"""
        amount = Decimal(str(invoice.total_amount_usd or 0))
        tax = amount * Decimal("7") * Decimal("1.003") * Decimal("0.1663")
        
        return f"【预计税金通知】\n\n发票号：{invoice.invoice_no}\n预计税金：¥{tax:.2f}"
    
    @staticmethod
    async def create_notifications(db: AsyncSession, invoice_id: int, user_id: int = 1) -> list[Notification]:
        """为新单证创建通知"""
        # 查询发票和产品明细
        from app.models import ImportInvoice, InvoiceProduct, Company
        from sqlalchemy.orm import selectinload
        
        invoice_result = await db.execute(
            select(ImportInvoice)
            .options(selectinload(ImportInvoice.processing_plant))
            .where(ImportInvoice.id == invoice_id)
        )
        invoice = invoice_result.scalar_one_or_none()
        if not invoice:
            return []
        
        products_result = await db.execute(
            select(InvoiceProduct).where(InvoiceProduct.invoice_id == invoice_id)
        )
        products = products_result.scalars().all()
        
        notifications = []
        now = datetime.now()
        
        # 获取加工厂显示（优先EU注册号 enterprise_registration_no，其次 name）
        processing_plant_display = None
        if invoice.processing_plant:
            # 关系已加载，直接取
            processing_plant_display = invoice.processing_plant.enterprise_registration_no or invoice.processing_plant.name
        elif invoice.processing_plant_id:
            # 如果关系没加载，直接查询
            company_result = await db.execute(
                select(Company).where(Company.id == invoice.processing_plant_id)
            )
            company = company_result.scalar_one_or_none()
            if company:
                processing_plant_display = company.enterprise_registration_no or company.name
        
        # 1. 预计到货通知
        arrival_text = InvoiceNotificationService.generate_arrival_notification(
            invoice, products, processing_plant_display
        )
        arrival_notification = Notification(
            user_id=user_id,
            title="预计到货通知",
            content=arrival_text,
            type="invoice_arrival",
            related_id=invoice_id,
            related_type="import_invoice",
            is_read=False,
            created_at=now,
            updated_at=now,
        )
        db.add(arrival_notification)
        notifications.append(arrival_notification)
        
        # 2. 预计税金通知
        tax_text = InvoiceNotificationService.generate_tax_notification(invoice)
        tax_notification = Notification(
            user_id=user_id,
            title="预计税金通知",
            content=tax_text,
            type="invoice_tax",
            related_id=invoice_id,
            related_type="import_invoice",
            is_read=False,
            created_at=now,
            updated_at=now,
        )
        db.add(tax_notification)
        notifications.append(tax_notification)
        
        await db.commit()
        return notifications

# 便捷函数
async def create_invoice_notifications(invoice_id: int, user_id: int = 1):
    """为新单证创建通知的便捷函数"""
    async with AsyncSessionLocal() as db:
        return await InvoiceNotificationService.create_notifications(db, invoice_id, user_id)
