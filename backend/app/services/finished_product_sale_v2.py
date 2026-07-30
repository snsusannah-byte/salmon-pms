"""
成品销售 Service 扩展（V2）
基于现有服务向后兼容添加：
- 销售子项支持（正品/配套/赠品）
- 关联宰杀日期
- 自动扣减包装物/配套/赠品库存

同时新增 FinishedProductSaleV2 / FinishedSaleProductV2 模型的 CRUD + 收款服务。
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    FinishedProductSale,
    FinishedProductSaleV2,
    FinishedProductReceipt,
    FinishedSaleProductV2,
    Product,
    ProductBOM,
    ProductPackaging,
)
from app.models.warehouse import ProductUnitConversion
from app.models.finished_product_v2 import (
    FinishedProductSaleItem,
    SaleItemType,
)


class FinishedProductSaleServiceV2:
    """成品销售服务V2扩展"""

    @staticmethod
    async def create_sale_with_items(
        db: AsyncSession,
        sale_data: dict,
        items: list[dict],
    ) -> FinishedProductSale:
        """创建销售（带子项）
        
        业务流程：
        1. 校验宰杀日期（必须已锁定且有可用肉）
        2. 扣减包装物库存（根据BOM和包装物配置）
        3. 扣减配套/赠品库存
        4. 创建销售记录
        5. 创建销售子项
        6. 更新宰杀记录的已售肉重
        """
        from app.services.daily_slaughter_service import DailySlaughterService
        from app.services.finished_product_sale_service import (
            FinishedProductSaleService,
        )
        from app.services.warehouse_service import WarehouseService
        
        # 1. 校验宰杀日期
        slaughter_date = sale_data.get("slaughter_date")
        total_weight_kg = Decimal(str(sale_data.get("total_weight_kg", 0)))
        
        if slaughter_date:
            slaughter_record = await DailySlaughterService.get_by_date(db, slaughter_date)
            if not slaughter_record:
                raise ValueError(f"宰杀日期 {slaughter_date} 不存在，请先登记宰杀记录")
            if not slaughter_record.is_locked:
                raise ValueError(f"宰杀日期 {slaughter_date} 尚未锁定，请先锁定成本")
            if slaughter_record.available_meat_kg < total_weight_kg:
                raise ValueError(
                    f"可用肉不足：日期 {slaughter_date} 可用 {slaughter_record.available_meat_kg}kg，"
                    f"需要 {total_weight_kg}kg"
                )
        
        # 2. 创建基础销售记录（使用现有服务）
        sale = await FinishedProductSaleService.create_sale(db, sale_data)
        
        # 3. 设置宰杀日期和总重量（新字段）
        if slaughter_date:
            sale.slaughter_date = slaughter_date
        if total_weight_kg:
            sale.total_weight_kg = total_weight_kg
        
        # 4. 处理销售子项
        total_main_weight = Decimal("0")
        for item_data in items:
            item_type = item_data.get("item_type", SaleItemType.MAIN.value)
            product_id = item_data["product_id"]
            
            # 创建子项
            weight_kg = None
            quantity = None
            amount = Decimal("0")
            
            if item_type == SaleItemType.MAIN.value:
                weight_kg = Decimal(str(item_data.get("weight_kg", 0)))
                total_main_weight += weight_kg
                unit_price = Decimal(str(item_data.get("unit_price", sale.unit_price)))
                amount = (weight_kg * unit_price).quantize(Decimal("0.01"))
            else:
                quantity = item_data.get("quantity", 0)
                unit_price = Decimal(str(item_data.get("unit_price", 0)))
                amount = (Decimal(str(quantity)) * unit_price).quantize(Decimal("0.01"))
            
            sale_item = FinishedProductSaleItem(
                sale_id=sale.id,
                item_type=item_type,
                product_id=product_id,
                weight_kg=weight_kg,
                quantity=quantity,
                unit_price=unit_price if unit_price > 0 else None,
                amount=amount,
                notes=item_data.get("notes"),
            )
            db.add(sale_item)
            
            # 扣减配套/赠品库存
            if item_type in (SaleItemType.GIFT.value, SaleItemType.ACCESSORY.value):
                try:
                    await WarehouseService.stock_out(
                        db,
                        product_id=product_id,
                        quantity=Decimal(str(quantity or 1)),
                        reason="sale",
                    )
                except ValueError:
                    # 库存不足警告但不阻止（业务上可能允许负库存）
                    pass
        
        # 5. 扣减包装物库存（根据主产品的BOM和包装物配置）
        await FinishedProductSaleServiceV2._deduct_packaging_stock(db, sale.product_id, sale.quantity)
        
        # 6. 更新宰杀记录的已售肉重
        if slaughter_date and total_main_weight > 0:
            await DailySlaughterService.update_sold_weight(db, slaughter_date, total_main_weight)
        
        await db.commit()
        await db.refresh(sale)
        return sale

    @staticmethod
    async def _deduct_packaging_stock(db: AsyncSession, product_id: int, sale_quantity: int):
        """扣减包装物库存"""
        from app.services.warehouse_service import WarehouseService
        
        # 查询BOM物料
        result = await db.execute(
            select(ProductBOM).where(ProductBOM.finished_product_id == product_id)
        )
        boms = result.scalars().all()
        
        for bom in boms:
            needed_qty = (bom.quantity * Decimal(str(sale_quantity))).quantize(Decimal("0.0001"))
            try:
                await WarehouseService.stock_out(
                    db,
                    product_id=bom.material_id,
                    quantity=needed_qty,
                    reason="packaging",
                )
            except ValueError:
                pass
        
        # 查询包装物配置
        result = await db.execute(
            select(ProductPackaging).where(ProductPackaging.product_id == product_id)
        )
        packagings = result.scalars().all()
        
        for pkg in packagings:
            needed_qty = (pkg.quantity * Decimal(str(sale_quantity))).quantize(Decimal("0.0001"))
            try:
                await WarehouseService.stock_out(
                    db,
                    product_id=pkg.material_id,
                    quantity=needed_qty,
                    reason="packaging",
                )
            except ValueError:
                pass

    @staticmethod
    async def delete_sale_v2(db: AsyncSession, sale: FinishedProductSale):
        """删除销售（恢复库存）"""
        from app.services.daily_slaughter_service import DailySlaughterService
        from app.services.warehouse_service import WarehouseService
        
        # 1. 恢复宰杀记录的已售肉重
        if sale.slaughter_date and sale.total_weight_kg:
            slaughter_record = await DailySlaughterService.get_by_date(db, sale.slaughter_date)
            if slaughter_record:
                slaughter_record.sold_meat_kg = (
                    slaughter_record.sold_meat_kg - sale.total_weight_kg
                ).quantize(Decimal("0.001"))
                if slaughter_record.sold_meat_kg < 0:
                    slaughter_record.sold_meat_kg = Decimal("0")
                slaughter_record.available_meat_kg = (
                    slaughter_record.meat_weight_kg
                    - slaughter_record.byproduct_trim_weight_kg
                    - slaughter_record.loss_weight_kg
                    - slaughter_record.sold_meat_kg
                ).quantize(Decimal("0.001"))
        
        # 2. 恢复配套/赠品库存
        result = await db.execute(
            select(FinishedProductSaleItem).where(FinishedProductSaleItem.sale_id == sale.id)
        )
        items = result.scalars().all()
        
        for item in items:
            if item.item_type in (SaleItemType.GIFT.value, SaleItemType.ACCESSORY.value) and item.quantity:
                try:
                    await WarehouseService.stock_in(
                        db,
                        product_id=item.product_id,
                        quantity=Decimal(str(item.quantity)),
                    )
                except Exception:
                    pass
        
        # 3. 恢复包装物库存
        await FinishedProductSaleServiceV2._restore_packaging_stock(db, sale.product_id, sale.quantity)
        
        # 4. 删除销售子项
        for item in items:
            await db.delete(item)
        
        # 5. 删除销售记录（使用现有服务）
        from app.services.finished_product_sale_service import (
            FinishedProductSaleService,
        )
        await FinishedProductSaleService.delete_sale(db, sale)

    @staticmethod
    async def _restore_packaging_stock(db: AsyncSession, product_id: int, sale_quantity: int):
        """恢复包装物库存"""
        from app.services.warehouse_service import WarehouseService
        
        result = await db.execute(
            select(ProductBOM).where(ProductBOM.finished_product_id == product_id)
        )
        boms = result.scalars().all()
        
        for bom in boms:
            restore_qty = (bom.quantity * Decimal(str(sale_quantity))).quantize(Decimal("0.0001"))
            try:
                await WarehouseService.stock_in(db, product_id=bom.material_id, quantity=restore_qty)
            except Exception:
                pass
        
        result = await db.execute(
            select(ProductPackaging).where(ProductPackaging.product_id == product_id)
        )
        packagings = result.scalars().all()
        
        for pkg in packagings:
            restore_qty = (pkg.quantity * Decimal(str(sale_quantity))).quantize(Decimal("0.0001"))
            try:
                await WarehouseService.stock_in(db, product_id=pkg.material_id, quantity=restore_qty)
            except Exception:
                pass

    @staticmethod
    async def get_sale_items(db: AsyncSession, sale_id: int) -> list[FinishedProductSaleItem]:
        """获取销售子项列表"""
        result = await db.execute(
            select(FinishedProductSaleItem)
            .where(FinishedProductSaleItem.sale_id == sale_id)
            .order_by(FinishedProductSaleItem.id)
        )
        return list(result.scalars().all())


class FinishedProductSaleV2Service:
    """成品销售 V2 模型服务（FinishedProductSaleV2 / FinishedSaleProductV2）"""

    @staticmethod
    async def list_sales(
        db: AsyncSession,
        sale_type: str | None = None,
        customer: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[FinishedProductSaleV2], int]:
        query = select(FinishedProductSaleV2).options(
            selectinload(FinishedProductSaleV2.products),
            selectinload(FinishedProductSaleV2.receipts),
        )
        count_query = select(func.count(FinishedProductSaleV2.id))

        filters = []
        if sale_type:
            filters.append(FinishedProductSaleV2.sale_type == sale_type)
        if customer:
            filters.append(FinishedProductSaleV2.customer.ilike(f"%{customer}%"))
        if start_date:
            filters.append(FinishedProductSaleV2.sale_date >= start_date)
        if end_date:
            filters.append(FinishedProductSaleV2.sale_date <= end_date)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        query = query.order_by(FinishedProductSaleV2.sale_date.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return list(items), total

    @staticmethod
    async def get_by_id(db: AsyncSession, sale_id: int) -> FinishedProductSaleV2 | None:
        result = await db.execute(
            select(FinishedProductSaleV2)
            .options(
                selectinload(FinishedProductSaleV2.products),
                selectinload(FinishedProductSaleV2.receipts),
            )
            .where(FinishedProductSaleV2.id == sale_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_sale(db: AsyncSession, data: dict) -> FinishedProductSaleV2:
        products_data = data.pop("products", []) or []
        sale_data = {k: v for k, v in data.items() if v is not None}

        # 确保金额字段为 Decimal
        for field in [
            "discount", "scan_fee", "rounding", "after_sales_adjustment",
            "commission", "balance_adjustment", "paid_amount", "total_amount",
            "actual_amount", "net_amount", "quantity", "weight", "unit_price",
        ]:
            if field in sale_data and sale_data[field] is not None:
                sale_data[field] = Decimal(str(sale_data[field]))
            elif field not in sale_data:
                sale_data[field] = Decimal("0")

        # 清理空字符串的关联采购单号
        if sale_data.get("source_no") == '':
            sale_data["source_no"] = None
        if sale_data.get("source_id") == 0:
            sale_data["source_id"] = None

        # 计算 net_amount
        sale_data["net_amount"] = FinishedProductSaleV2Service._calculate_net_amount(
            sale_data
        )

        # 如果没有提供 sale_no，先使用临时唯一值占位
        if not sale_data.get("sale_no"):
            sale_data["sale_no"] = f"TMP-{uuid4().hex[:12]}"

        sale = FinishedProductSaleV2(**sale_data)
        db.add(sale)
        await db.commit()
        await db.refresh(sale)

        # 创建产品明细
        for raw_data in products_data:
            item_data = await FinishedProductSaleV2Service._apply_unit_conversion(db, raw_data)
            item = FinishedProductSaleV2Service._build_product_item(sale.id, item_data)
            db.add(item)
        await db.commit()
        await db.refresh(sale)

        # 如果有临时 sale_no，更新为正式编号
        if sale.sale_no.startswith("TMP-"):
            sale_date = sale.sale_date or date.today()
            sale.sale_no = (
                f"SOV2-{sale_date.strftime('%Y%m%d')}-{sale.id:04d}"
            )
            await db.commit()
            await db.refresh(sale)

        return sale

    @staticmethod
    async def update_sale(
        db: AsyncSession, sale: FinishedProductSaleV2, data: dict
    ) -> FinishedProductSaleV2:
        products_data = data.pop("products", None)
        update_data = {k: v for k, v in data.items() if v is not None}

        for field in [
            "discount", "scan_fee", "rounding", "after_sales_adjustment",
            "commission", "balance_adjustment", "paid_amount", "total_amount",
            "actual_amount", "net_amount", "quantity", "weight", "unit_price",
        ]:
            if field in update_data:
                update_data[field] = Decimal(str(update_data[field]))

        # 清理空字符串的关联采购单号
        if update_data.get("source_no") == '':
            update_data["source_no"] = None
        if update_data.get("source_id") == 0:
            update_data["source_id"] = None

        for field, value in update_data.items():
            setattr(sale, field, value)

        # 重新计算 net_amount
        sale.net_amount = FinishedProductSaleV2Service._calculate_net_amount(
            sale.__dict__
        )

        # 替换产品明细
        if products_data is not None:
            # 删除旧明细
            for product in list(sale.products or []):
                await db.delete(product)
            # 创建新明细
            for raw_data in products_data:
                item_data = await FinishedProductSaleV2Service._apply_unit_conversion(db, raw_data)
                item = FinishedProductSaleV2Service._build_product_item(
                    sale.id, item_data
                )
                db.add(item)

        await db.commit()
        await db.refresh(sale)
        return sale

    @staticmethod
    async def delete_sale(db: AsyncSession, sale: FinishedProductSaleV2) -> None:
        for product in list(sale.products or []):
            await db.delete(product)
        for receipt in list(sale.receipts or []):
            await db.delete(receipt)
        await db.delete(sale)
        await db.commit()

    @staticmethod
    async def add_receipt(
        db: AsyncSession, sale: FinishedProductSaleV2, data: dict
    ) -> FinishedProductReceipt:
        for field in ["amount"]:
            if field in data and data[field] is not None:
                data[field] = Decimal(str(data[field]))

        # 记录创建时单据的应付/待付金额
        if data.get("payable_amount") is None:
            data["payable_amount"] = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))

        receipt = FinishedProductReceipt(sale_v2_id=sale.id, **data)
        db.add(receipt)
        await db.commit()
        await db.refresh(receipt)

        await FinishedProductSaleV2Service._update_paid_amount(db, sale)
        return receipt

    @staticmethod
    async def delete_receipt(db: AsyncSession, receipt_id: int) -> None:
        result = await db.execute(
            select(FinishedProductReceipt).where(FinishedProductReceipt.id == receipt_id)
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            raise HTTPException(status_code=404, detail="收款记录不存在")

        sale = await FinishedProductSaleV2Service.get_by_id(db, receipt.sale_v2_id)
        await db.delete(receipt)
        await db.commit()

        if sale:
            await FinishedProductSaleV2Service._update_paid_amount(db, sale)

    @staticmethod
    async def _update_paid_amount(
        db: AsyncSession, sale: FinishedProductSaleV2
    ) -> None:
        result = await db.execute(
            select(func.sum(FinishedProductReceipt.amount)).where(
                FinishedProductReceipt.sale_v2_id == sale.id
            )
        )
        total_paid = result.scalar() or Decimal("0")
        sale.paid_amount = total_paid

        # 更新 paid 状态：1 表示已付清
        if sale.paid_amount >= (sale.net_amount or Decimal("0")):
            sale.paid = 1
        else:
            sale.paid = 0

        await db.commit()

    @staticmethod
    def _calculate_net_amount(sale_data: dict) -> Decimal:
        total_amount = Decimal(str(sale_data.get("total_amount") or 0))
        discount = Decimal(str(sale_data.get("discount") or 0))
        scan_fee = Decimal(str(sale_data.get("scan_fee") or 0))
        commission = Decimal(str(sale_data.get("commission") or 0))
        rounding = Decimal(str(sale_data.get("rounding") or 0))
        after_sales_adjustment = Decimal(
            str(sale_data.get("after_sales_adjustment") or 0)
        )
        balance_adjustment = Decimal(str(sale_data.get("balance_adjustment") or 0))
        return (
            total_amount
            - discount
            - scan_fee
            - commission
            + rounding
            + after_sales_adjustment
            + balance_adjustment
        ).quantize(Decimal("0.01"))

    @staticmethod
    def _build_product_item(sale_id: int, item_data: dict) -> FinishedSaleProductV2:
        for field in [
            "weight_kg", "unit_price", "total_amount", "commission_rate",
            "commission_amount", "after_sales_adjustment", "base_quantity",
        ]:
            if field in item_data and item_data[field] is not None:
                item_data[field] = Decimal(str(item_data[field]))
            elif field not in item_data:
                item_data[field] = Decimal("0")
        if "box_count" not in item_data:
            item_data["box_count"] = 0
        return FinishedSaleProductV2(sale_id=sale_id, **item_data)

    @staticmethod
    async def _resolve_product_id(
        db: AsyncSession, item_data: dict
    ) -> int | None:
        """根据 sale line 信息解析对应的库存产品ID。"""
        if item_data.get("product_id"):
            return int(item_data["product_id"])
        product_name = item_data.get("product_name") or item_data.get("product_spec")
        if not product_name:
            return None
        result = await db.execute(
            select(Product.id).where(Product.name == product_name).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _calculate_base_quantity(
        db: AsyncSession, item_data: dict
    ) -> tuple[Decimal | None, str | None]:
        """计算销售行的基础数量和销售单位。

        返回 (base_quantity, sale_unit)。
        当 sale_unit 与产品基础单位不一致时，通过 ProductUnitConversion 换算。
        """
        product_id = await FinishedProductSaleV2Service._resolve_product_id(
            db, item_data
        )
        if not product_id:
            return None, item_data.get("sale_unit")

        product_result = await db.execute(
            select(Product.unit).where(Product.id == product_id)
        )
        base_unit = product_result.scalar_one_or_none() or ""

        sale_unit = item_data.get("sale_unit") or base_unit
        if not sale_unit:
            sale_unit = base_unit

        quantity = Decimal(str(item_data.get("box_count") or item_data.get("weight_kg") or 0))
        if sale_unit == base_unit or not base_unit:
            # 销售单位即基础单位，无需换算
            return (Decimal(str(quantity)).quantize(Decimal("0.01"))
                    if quantity else Decimal("0")), sale_unit

        # 查找换算规则（sale_unit -> base_unit）
        conversion_result = await db.execute(
            select(ProductUnitConversion.ratio)
            .where(
                ProductUnitConversion.product_id == product_id,
                ProductUnitConversion.from_unit == sale_unit,
                ProductUnitConversion.to_unit == base_unit,
            )
            .limit(1)
        )
        ratio = conversion_result.scalar_one_or_none()
        if ratio:
            base_quantity = (quantity * ratio).quantize(Decimal("0.01"))
            return base_quantity, sale_unit

        # 尝试反向换算（base_unit -> sale_unit 取倒数）
        reverse_result = await db.execute(
            select(ProductUnitConversion.ratio)
            .where(
                ProductUnitConversion.product_id == product_id,
                ProductUnitConversion.from_unit == base_unit,
                ProductUnitConversion.to_unit == sale_unit,
            )
            .limit(1)
        )
        reverse_ratio = reverse_result.scalar_one_or_none()
        if reverse_ratio and reverse_ratio > 0:
            base_quantity = (quantity / reverse_ratio).quantize(Decimal("0.01"))
            return base_quantity, sale_unit

        # 无法换算，回退为基础单位数量
        return (Decimal(str(quantity)).quantize(Decimal("0.01"))
                if quantity else Decimal("0")), sale_unit

    @staticmethod
    async def _apply_unit_conversion(
        db: AsyncSession, item_data: dict
    ) -> dict:
        """在 item_data 中填充 product_id / sale_unit / base_quantity（如果需要）。"""
        item_data = dict(item_data)
        product_id = await FinishedProductSaleV2Service._resolve_product_id(db, item_data)
        if product_id:
            item_data["product_id"] = product_id
        base_quantity, sale_unit = await FinishedProductSaleV2Service._calculate_base_quantity(
            db, item_data
        )
        item_data["sale_unit"] = sale_unit
        item_data["base_quantity"] = base_quantity
        return item_data
