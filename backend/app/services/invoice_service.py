from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImportInvoice, InvoiceProduct, InvoiceStatus, ExchangeStatus
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceProductCreate, InvoiceProductUpdate


class InvoiceService:
    """进口单证服务"""
    
    @staticmethod
    async def get_by_id(db: AsyncSession, invoice_id: int) -> Optional[ImportInvoice]:
        """根据ID获取发票（包含产品明细和关联主体）"""
        result = await db.execute(
            select(ImportInvoice)
            .options(
                selectinload(ImportInvoice.products),
                selectinload(ImportInvoice.processing_plant),
                selectinload(ImportInvoice.fish_farm),
                selectinload(ImportInvoice.exporter),
            )
            .where(ImportInvoice.id == invoice_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_invoice_no(db: AsyncSession, invoice_no: str) -> Optional[ImportInvoice]:
        """根据发票编号获取"""
        result = await db.execute(
            select(ImportInvoice).where(ImportInvoice.invoice_no == invoice_no)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_invoices(
        db: AsyncSession,
        customs_status: Optional[InvoiceStatus] = None,
        exchange_status: Optional[ExchangeStatus] = None,
        processing_plant_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        exclude_assigned: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[ImportInvoice], int]:
        """获取发票列表"""
        query = select(ImportInvoice)
        count_query = select(func.count(ImportInvoice.id))
        
        # 构建过滤条件
        filters = []
        if customs_status:
            filters.append(ImportInvoice.customs_status == customs_status)
        if exchange_status:
            filters.append(ImportInvoice.exchange_status == exchange_status)
        if processing_plant_id:
            filters.append(ImportInvoice.processing_plant_id == processing_plant_id)
        if start_date:
            filters.append(ImportInvoice.invoice_date >= start_date)
        if end_date:
            filters.append(ImportInvoice.invoice_date <= end_date)
        if search:
            search_pattern = f"%{search}%"
            filters.append(ImportInvoice.invoice_no.ilike(search_pattern))
        
        if exclude_assigned:
            # 排除已关联批次的发票
            from app.models import BatchInvoice
            subquery = select(BatchInvoice.invoice_id)
            filters.append(ImportInvoice.id.not_in(subquery))
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # 排序（发票日期降序）
        query = query.order_by(ImportInvoice.invoice_date.desc())
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return list(items), total
    
    @staticmethod
    async def generate_invoice_no(db: AsyncSession, invoice_date: date) -> str:
        """根据发票日期自动生成编号: YYYYMMDD-NNN"""
        date_str = invoice_date.strftime("%Y%m%d")
        prefix = f"{date_str}-"
        
        # 查询当天已有的最大序号
        result = await db.execute(
            select(ImportInvoice.invoice_no)
            .where(ImportInvoice.invoice_no.like(f"{prefix}%"))
            .order_by(ImportInvoice.invoice_no.desc())
        )
        codes = result.scalars().all()
        
        max_num = 0
        for code in codes:
            try:
                num = int(code.split("-")[-1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                continue
        
        new_num = max_num + 1
        return f"{prefix}{new_num:03d}"

    @staticmethod
    async def create(db: AsyncSession, data: InvoiceCreate) -> ImportInvoice:
        """创建发票"""
        # 提取产品明细
        products_data = data.products if data.products else []
        invoice_data = data.model_dump(exclude={"products"}, exclude_unset=True)
        
        # PostgreSQL 外键约束：把 0 转为 None
        for fk_field in ["processing_plant_id", "fish_farm_id", "exporter_id"]:
            if fk_field in invoice_data and invoice_data[fk_field] == 0:
                invoice_data[fk_field] = None
        
        # 处理日期
        for field in ["invoice_date", "kill_date", "arrival_date"]:
            if field in invoice_data and invoice_data[field]:
                if isinstance(invoice_data[field], str):
                    invoice_data[field] = date.fromisoformat(invoice_data[field])
        
        # 自动生成发票编号（如果未提供）
        if not invoice_data.get("invoice_no"):
            inv_date = invoice_data.get("invoice_date")
            if inv_date:
                invoice_data["invoice_no"] = await InvoiceService.generate_invoice_no(db, inv_date)
        
        # 计算总金额/总箱数/总重量
        if products_data:
            invoice_data["total_amount_usd"] = sum(
                p.total_amount for p in products_data
            )
            invoice_data["total_boxes"] = sum(
                p.box_count for p in products_data
            )
            invoice_data["total_weight_kg"] = sum(
                p.net_weight_kg for p in products_data
            )
        
        invoice = ImportInvoice(**invoice_data)
        db.add(invoice)
        
        # 创建产品明细（此时 invoice.id 还未分配，使用对象关联）
        for product_data in products_data:
            product = InvoiceProduct(
                **product_data.model_dump()
            )
            product.invoice = invoice  # 通过关系关联
            db.add(product)
        
        await db.commit()
        await db.refresh(invoice)
        
        # 生成通知（预计到货 + 预计税金）
        try:
            from app.services.notification_service import InvoiceNotificationService
            await InvoiceNotificationService.create_notifications(db, invoice.id)
        except Exception as e:
            print(f"通知生成失败: {e}")
        
        return invoice
    
    @staticmethod
    async def update(db: AsyncSession, invoice: ImportInvoice, data: InvoiceUpdate) -> ImportInvoice:
        """更新发票（支持更新产品明细）"""
        if invoice.is_locked:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"发票 {invoice.invoice_no} 已锁定，不能修改"
            )
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 提取产品明细
        products_data = update_data.pop("products", None)
        
        # 处理日期
        for field in ["invoice_date", "kill_date", "arrival_date"]:
            if field in update_data and update_data[field]:
                if isinstance(update_data[field], str):
                    update_data[field] = date.fromisoformat(update_data[field])
        
        # 更新主表字段
        for field, value in update_data.items():
            if value is not None:
                setattr(invoice, field, value)
        
        # 如果提供了产品明细，替换旧的产品明细
        if products_data is not None:
            # 删除旧的产品明细
            await db.execute(
                delete(InvoiceProduct).where(InvoiceProduct.invoice_id == invoice.id)
            )
            
            # 创建新的产品明细
            total_amount = Decimal("0")
            total_boxes = 0
            total_weight = Decimal("0")
            
            for product_data in products_data:
                # product_data 是字典（已从 Pydantic model_dump）
                product = InvoiceProduct(
                    invoice_id=invoice.id,
                    **product_data
                )
                db.add(product)
                total_amount += Decimal(str(product_data.get("total_amount", 0)))
                total_boxes += product_data.get("box_count", 0)
                total_weight += Decimal(str(product_data.get("net_weight_kg", 0)))
            
            # 更新汇总字段
            invoice.total_amount_usd = total_amount
            invoice.total_boxes = total_boxes
            invoice.total_weight_kg = total_weight
        
        await db.commit()
        await db.refresh(invoice)
        return invoice
    
    @staticmethod
    async def delete(db: AsyncSession, invoice: ImportInvoice) -> None:
        """删除发票（级联删除产品明细）"""
        if invoice.is_locked:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"发票 {invoice.invoice_no} 已锁定，不能删除"
            )
        
        # 手动删除关联的产品明细（避免外键约束问题）
        await db.execute(
            delete(InvoiceProduct).where(InvoiceProduct.invoice_id == invoice.id)
        )
        
        await db.delete(invoice)
        await db.commit()
    
    @staticmethod
    async def add_product(db: AsyncSession, invoice_id: int, data: InvoiceProductCreate) -> InvoiceProduct:
        """添加产品明细"""
        invoice = await InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="发票不存在")
        
        if invoice.is_locked:
            raise HTTPException(status_code=400, detail="发票已锁定，不能添加产品")
        
        product = InvoiceProduct(
            invoice_id=invoice_id,
            **data.model_dump()
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        
        # 更新发票汇总数据
        await InvoiceService._recalculate_totals(db, invoice)
        
        return product
    
    @staticmethod
    async def update_product(db: AsyncSession, product: InvoiceProduct, data: InvoiceProductUpdate) -> InvoiceProduct:
        """更新产品明细"""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        await db.commit()
        await db.refresh(product)
        
        # 更新发票汇总数据
        invoice = await InvoiceService.get_by_id(db, product.invoice_id)
        if invoice:
            await InvoiceService._recalculate_totals(db, invoice)
        
        return product
    
    @staticmethod
    async def delete_product(db: AsyncSession, product: InvoiceProduct) -> None:
        """删除产品明细"""
        invoice = await InvoiceService.get_by_id(db, product.invoice_id)
        if invoice and invoice.is_locked:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="发票已锁定，不能删除产品")
        
        await db.delete(product)
        await db.commit()
        
        if invoice:
            await InvoiceService._recalculate_totals(db, invoice)
    
    @staticmethod
    async def _recalculate_totals(db: AsyncSession, invoice: ImportInvoice) -> None:
        """重新计算发票汇总数据"""
        result = await db.execute(
            select(
                func.sum(InvoiceProduct.total_amount),
                func.sum(InvoiceProduct.box_count),
                func.sum(InvoiceProduct.net_weight_kg),
            ).where(InvoiceProduct.invoice_id == invoice.id)
        )
        totals = result.one()
        
        invoice.total_amount_usd = totals[0] or Decimal("0")
        invoice.total_boxes = totals[1] or 0
        invoice.total_weight_kg = totals[2] or Decimal("0")
        
        await db.commit()
    
    @staticmethod
    async def get_summary(db: AsyncSession) -> dict:
        """获取发票汇总统计"""
        # 总统计
        total_result = await db.execute(
            select(
                func.count(ImportInvoice.id),
                func.sum(ImportInvoice.total_amount_usd),
            )
        )
        total_count, total_amount = total_result.one()
        
        # 本月统计
        now = datetime.now()
        this_month_start = date(now.year, now.month, 1)
        month_result = await db.execute(
            select(
                func.count(ImportInvoice.id),
                func.sum(ImportInvoice.total_amount_usd),
            ).where(ImportInvoice.invoice_date >= this_month_start)
        )
        month_count, month_amount = month_result.one()
        
        # 待购汇统计
        pending_result = await db.execute(
            select(
                func.count(ImportInvoice.id),
                func.sum(ImportInvoice.total_amount_usd),
            ).where(
                ImportInvoice.exchange_status.in_([
                    ExchangeStatus.NOT_EXCHANGED,
                    ExchangeStatus.PARTIAL,
                ])
            )
        )
        pending_count, pending_amount = pending_result.one()
        
        return {
            "total_count": total_count or 0,
            "total_amount_usd": total_amount or Decimal("0"),
            "this_month_count": month_count or 0,
            "this_month_amount": month_amount or Decimal("0"),
            "pending_exchange_count": pending_count or 0,
            "pending_exchange_amount": pending_amount or Decimal("0"),
        }
