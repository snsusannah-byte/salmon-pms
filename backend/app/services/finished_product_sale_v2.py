"""
成品销售 Service 扩展（V2）
基于现有服务向后兼容添加：
- 销售子项支持（正品/配套/赠品）
- 关联宰杀日期
- 自动扣减包装物/配套/赠品库存
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finished_product_v2 import (
    FinishedProductSaleItem,
    SaleItemType,
    WarehouseStock,
    DailySlaughterRecord,
)
from app.models import (
    Product,
    ProductCategory,
    ProductBOM,
    ProductPackaging,
    Company,
    FinishedProductSale,
)


class FinishedProductSaleServiceV2:
    """成品销售服务V2扩展"""

    @staticmethod
    async def create_sale_with_items(
        db: AsyncSession,
        sale_data: dict,
        items: List[dict],
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
        from app.services.finished_product_sale_service import FinishedProductSaleService
        from app.services.daily_slaughter_service import DailySlaughterService
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
                except ValueError as e:
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
                except:
                    pass
        
        # 3. 恢复包装物库存
        await FinishedProductSaleServiceV2._restore_packaging_stock(db, sale.product_id, sale.quantity)
        
        # 4. 删除销售子项
        for item in items:
            await db.delete(item)
        
        # 5. 删除销售记录（使用现有服务）
        from app.services.finished_product_sale_service import FinishedProductSaleService
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
            except:
                pass
        
        result = await db.execute(
            select(ProductPackaging).where(ProductPackaging.product_id == product_id)
        )
        packagings = result.scalars().all()
        
        for pkg in packagings:
            restore_qty = (pkg.quantity * Decimal(str(sale_quantity))).quantize(Decimal("0.0001"))
            try:
                await WarehouseService.stock_in(db, product_id=pkg.material_id, quantity=restore_qty)
            except:
                pass

    @staticmethod
    async def get_sale_items(db: AsyncSession, sale_id: int) -> List[FinishedProductSaleItem]:
        """获取销售子项列表"""
        result = await db.execute(
            select(FinishedProductSaleItem)
            .where(FinishedProductSaleItem.sale_id == sale_id)
            .order_by(FinishedProductSaleItem.id)
        )
        return list(result.scalars().all())
