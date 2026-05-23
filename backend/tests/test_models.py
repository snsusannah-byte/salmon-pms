"""核心模型测试"""
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Company, CompanyType, Product, ProductCategory


class TestCompany:
    """公司/客户模型测试"""

    async def test_create_company(self, db_session):
        """测试创建公司记录"""
        company = Company(
            name="测试公司",
            code="TEST001",
            type=CompanyType.CUSTOMER,
        )
        db_session.add(company)
        await db_session.commit()
        await db_session.refresh(company)

        assert company.id is not None
        assert company.name == "测试公司"
        assert company.code == "TEST001"
        assert company.type == CompanyType.CUSTOMER

    async def test_create_company_with_defaults(self, db_session):
        """测试默认值"""
        company = Company(
            name="默认公司",
            code="DEFAULT001",
            type=CompanyType.SUPPLIER,
        )
        db_session.add(company)
        await db_session.commit()

        assert company.currency == "CNY"
        assert company.is_active is True

    async def test_company_type_enum(self, db_session):
        """测试公司类型枚举"""
        types = [CompanyType.CUSTOMER, CompanyType.SUPPLIER,
                 CompanyType.PROCESSING_PLANT, CompanyType.FISH_FARM,
                 CompanyType.EXPORTER]
        for t in types:
            company = Company(name=f"测试-{t.value}", code=f"T-{t.value}", type=t)
            db_session.add(company)
        await db_session.commit()

        result = await db_session.execute(
            select(Company).where(Company.code.like("T-%"))
        )
        companies = result.scalars().all()
        assert len(companies) == 5


class TestProduct:
    """产品模型测试"""

    async def test_create_product(self, db_session):
        """测试创建产品"""
        product = Product(
            name="挪威三文鱼",
            code="NOR-SAL-01",
            category=ProductCategory.WHOLE_FISH,
            unit="kg",
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        assert product.id is not None
        assert product.name == "挪威三文鱼"
        assert product.category == ProductCategory.WHOLE_FISH
        assert product.unit == "kg"
        assert product.is_active is True

    async def test_create_finished_product(self, db_session):
        """测试创建成品肉产品"""
        product = Product(
            name="成品鱼肉",
            code="FIN-MEAT-01",
            category=ProductCategory.FINISHED_PRODUCT,
            unit="kg",
        )
        db_session.add(product)
        await db_session.commit()

        result = await db_session.execute(
            select(Product).where(Product.category == ProductCategory.FINISHED_PRODUCT)
        )
        products = result.scalars().all()
        assert len(products) == 1
        assert products[0].name == "成品鱼肉"

    async def test_product_decimal_fields(self, db_session):
        """测试 Decimal 字段精度"""
        product = Product(
            name="测试产品",
            code="TEST-DEC",
            category=ProductCategory.WHOLE_FISH,
            unit="kg",
            cost_price=Decimal("1234567.89"),
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        assert product.cost_price == Decimal("1234567.89")
