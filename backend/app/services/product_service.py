from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date

from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, ProductBOM, ProductCategory
from app.schemas.product import ProductCreate, ProductUpdate, ProductBOMCreate, ProductBOMUpdate


class ProductService:
    """产品管理服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
        """根据ID获取产品"""
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_products(
        db: AsyncSession,
        category: Optional[ProductCategory] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Product], int]:
        """获取产品列表"""
        query = select(Product)
        count_query = select(func.count(Product.id))

        filters = []
        if category:
            filters.append(Product.category == category)
        if is_active is not None:
            filters.append(Product.is_active == is_active)
        if search:
            filters.append(
                and_(
                    Product.name.ilike(f"%{search}%"),
                    Product.code.ilike(f"%{search}%"),
                )
            )

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        query = query.order_by(Product.category, Product.code).offset(skip).limit(limit)

        result = await db.execute(query)
        total_result = await db.execute(count_query)

        return result.scalars().all(), total_result.scalar()

    @staticmethod
    async def generate_code(db: AsyncSession, category: str) -> str:
        """根据分类自动生成产品编码"""
        prefix_map = {
            "whole_fish": "WF",
            "finished_product": "FP",
            "byproduct": "BP",
            "bom_material": "BM",
        }
        prefix = prefix_map.get(category, "PR")

        # 查询该分类下当前最大编号
        result = await db.execute(
            select(Product.code)
            .where(Product.category == category)
            .where(Product.code.like(f"{prefix}-%"))
            .order_by(Product.code.desc())
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
        return f"{prefix}-{new_num:03d}"

    @staticmethod
    async def create(db: AsyncSession, data: ProductCreate) -> Product:
        """创建产品"""
        code = data.code
        if not code:
            code = await ProductService.generate_code(db, data.category)

        # 成品名称自动生成：冰鲜三文鱼 + 规格编码
        name = data.name
        if data.category == "finished_product" and not name:
            spec = data.spec or ""
            if not spec and data.series_code and data.portion_weight_g and data.portion_boxes:
                spec = f"{data.series_code}{data.portion_weight_g}{data.portion_boxes}"
            if spec:
                name = f"冰鲜三文鱼{spec}"
            else:
                name = "冰鲜三文鱼"

        product = Product(
            category=data.category,
            code=code,
            name=name,
            spec=data.spec,
            unit=data.unit,
            unit_weight_kg=data.unit_weight_kg,
            series_code=data.series_code,
            series_name=data.series_name,
            portion_weight_g=data.portion_weight_g,
            portion_boxes=data.portion_boxes,
            is_active=data.is_active,
            notes=data.notes,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def update(db: AsyncSession, product_id: int, data: ProductUpdate) -> Optional[Product]:
        """更新产品"""
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def delete(db: AsyncSession, product_id: int) -> bool:
        """删除产品"""
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            return False

        await db.delete(product)
        await db.commit()
        return True

    # ==================== BOM管理 ====================

    @staticmethod
    async def get_boms(db: AsyncSession, finished_product_id: int) -> List[ProductBOM]:
        """获取成品BOM列表"""
        result = await db.execute(
            select(ProductBOM).where(ProductBOM.finished_product_id == finished_product_id)
        )
        return result.scalars().all()

    @staticmethod
    async def create_bom(db: AsyncSession, finished_product_id: int, data: ProductBOMCreate) -> ProductBOM:
        """创建BOM"""
        bom = ProductBOM(
            finished_product_id=finished_product_id,
            material_id=data.material_id,
            quantity=data.quantity,
            unit=data.unit,
            notes=data.notes,
        )
        db.add(bom)
        await db.commit()
        await db.refresh(bom)
        return bom

    @staticmethod
    async def update_bom(db: AsyncSession, bom_id: int, data: ProductBOMUpdate) -> Optional[ProductBOM]:
        """更新BOM"""
        result = await db.execute(
            select(ProductBOM).where(ProductBOM.id == bom_id)
        )
        bom = result.scalar_one_or_none()
        if not bom:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(bom, field, value)

        await db.commit()
        await db.refresh(bom)
        return bom

    @staticmethod
    async def delete_bom(db: AsyncSession, bom_id: int) -> bool:
        """删除BOM"""
        result = await db.execute(
            select(ProductBOM).where(ProductBOM.id == bom_id)
        )
        bom = result.scalar_one_or_none()
        if not bom:
            return False

        await db.delete(bom)
        await db.commit()
        return True

    @staticmethod
    async def get_series_options(db: AsyncSession) -> dict:
        """获取成品系列选项（系列代号 + 系列名称），用于下拉选择"""
        result = await db.execute(
            select(Product.series_code, Product.series_name)
            .where(Product.category == ProductCategory.FINISHED_PRODUCT)
            .where(Product.series_code.isnot(None))
            .distinct()
            .order_by(Product.series_code)
        )
        rows = result.all()

        codes = []
        names = []
        for row in rows:
            if row[0] and row[0] not in codes:
                codes.append(row[0])
            if row[1] and row[1] not in names:
                names.append(row[1])

        return {"series_codes": codes, "series_names": names}

    # ==================== 包装物管理 ====================

    @staticmethod
    async def get_packagings(db: AsyncSession, product_id: int) -> List[ProductPackaging]:
        """获取成品包装物清单"""
        from app.models import ProductPackaging
        result = await db.execute(
            select(ProductPackaging).where(ProductPackaging.product_id == product_id)
        )
        return result.scalars().all()

    @staticmethod
    async def create_packaging(db: AsyncSession, product_id: int, data) -> ProductPackaging:
        """创建包装物"""
        from app.models import ProductPackaging
        packaging = ProductPackaging(
            product_id=product_id,
            level=data.level,
            material_id=data.material_id,
            quantity=data.quantity,
            unit=data.unit,
            notes=data.notes,
        )
        db.add(packaging)
        await db.commit()
        await db.refresh(packaging)
        return packaging

    @staticmethod
    async def update_packaging(db: AsyncSession, packaging_id: int, data) -> Optional[ProductPackaging]:
        """更新包装物"""
        from app.models import ProductPackaging
        result = await db.execute(
            select(ProductPackaging).where(ProductPackaging.id == packaging_id)
        )
        packaging = result.scalar_one_or_none()
        if not packaging:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(packaging, field, value)

        await db.commit()
        await db.refresh(packaging)
        return packaging

    @staticmethod
    async def delete_packaging(db: AsyncSession, packaging_id: int) -> bool:
        """删除包装物"""
        from app.models import ProductPackaging
        result = await db.execute(
            select(ProductPackaging).where(ProductPackaging.id == packaging_id)
        )
        packaging = result.scalar_one_or_none()
        if not packaging:
            return False

        await db.delete(packaging)
        await db.commit()
        return True
