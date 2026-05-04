from fastapi import HTTPException
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Company, CompanyType
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyService:
    """主体管理服务"""
    
    @staticmethod
    async def get_by_id(db: AsyncSession, company_id: int) -> Optional[Company]:
        """根据ID获取主体"""
        result = await db.execute(select(Company).where(Company.id == company_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_code(db: AsyncSession, code: str, include_inactive: bool = False) -> Optional[Company]:
        """根据编码获取主体
        
        Args:
            include_inactive: 是否包含已删除（软删除）的主体，默认不包含
        """
        query = select(Company).where(Company.code == code)
        if not include_inactive:
            query = query.where(Company.is_active == True)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_or_create_customer(
        db: AsyncSession,
        name: str,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        customer_category: Optional[str] = None,
    ) -> Company:
        """根据名称查找或创建客户（去重逻辑）
        
        规则：
        1. 先按 name 精确匹配活跃客户
        2. 如不存在，创建新客户
        3. 返回客户对象
        """
        from app.models import CompanyType
        
        # 查找同名活跃客户
        result = await db.execute(
            select(Company)
            .where(Company.type == CompanyType.CUSTOMER)
            .where(Company.is_active == True)
            .where(Company.name == name)
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 更新已有客户信息（如提供的新信息非空）
            updated = False
            if contact_person and not existing.contact_person:
                existing.contact_person = contact_person
                updated = True
            if phone and not existing.phone:
                existing.phone = phone
                updated = True
            if address and not existing.address:
                existing.address = address
                updated = True
            if customer_category and not existing.customer_category:
                from app.models import CustomerCategory
                try:
                    existing.customer_category = CustomerCategory(customer_category)
                    updated = True
                except ValueError:
                    pass
            if updated:
                await db.commit()
                await db.refresh(existing)
            return existing
        
        # 创建新客户
        from app.models import CustomerCategory
        cat_enum = None
        if customer_category:
            try:
                cat_enum = CustomerCategory(customer_category)
            except ValueError:
                pass
        
        company = Company(
            name=name,
            type=CompanyType.CUSTOMER,
            contact_person=contact_person,
            phone=phone,
            address=address,
            customer_category=cat_enum,
            credit_limit=Decimal("0"),
            is_active=True,
        )
        db.add(company)
        await db.commit()
        await db.refresh(company)
        return company
    
    @staticmethod
    async def list_companies(
        db: AsyncSession,
        type: Optional[CompanyType] = None,
        exclude_type: Optional[CompanyType] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Company], int]:
        """获取主体列表
        
        Returns:
            (items, total) - 数据列表和总数
        """
        # 构建查询条件
        query = select(Company)
        count_query = select(func.count(Company.id))
        
        if type:
            query = query.where(Company.type == type)
            count_query = count_query.where(Company.type == type)
        
        if exclude_type:
            query = query.where(Company.type != exclude_type)
            count_query = count_query.where(Company.type != exclude_type)
        
        if is_active is not None:
            query = query.where(Company.is_active == is_active)
            count_query = count_query.where(Company.is_active == is_active)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                Company.name.ilike(search_pattern) | 
                Company.chinese_name.ilike(search_pattern) |
                Company.code.ilike(search_pattern) |
                Company.registration_code.ilike(search_pattern) |
                Company.contact_person.ilike(search_pattern)
            )
            count_query = count_query.where(
                Company.name.ilike(search_pattern) | 
                Company.chinese_name.ilike(search_pattern) |
                Company.code.ilike(search_pattern) |
                Company.registration_code.ilike(search_pattern) |
                Company.contact_person.ilike(search_pattern)
            )
        
        # 排序（名称升序）
        query = query.order_by(Company.name)
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        # 执行查询
        result = await db.execute(query)
        items = result.scalars().all()
        
        # 查询总数
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return list(items), total
    
    @staticmethod
    async def create(db: AsyncSession, data: CompanyCreate) -> Company:
        """创建主体"""
        dump_data = data.model_dump(exclude_unset=True)
        
        # 检查编码是否被活跃主体占用
        if dump_data.get("code"):
            existing = await CompanyService.get_by_code(db, dump_data["code"])
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"编码 '{dump_data['code']}' 已被主体 '{existing.name}' 使用"
                )
        
        # 处理合作日期字符串转 date 对象
        if "cooperation_date" in dump_data and dump_data["cooperation_date"]:
            try:
                from datetime import date
                dump_data["cooperation_date"] = date.fromisoformat(dump_data["cooperation_date"])
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"合作日期格式错误: '{dump_data['cooperation_date']}'，应为 YYYY-MM-DD 格式"
                )
        
        company = Company(**dump_data)
        db.add(company)
        await db.commit()
        await db.refresh(company)
        return company
    
    @staticmethod
    async def update(db: AsyncSession, company: Company, data: CompanyUpdate) -> Company:
        """更新主体"""
        update_data = data.model_dump(exclude_unset=True)
        
        # 检查编码是否被其他活跃主体占用
        if update_data.get("code") and update_data["code"] != company.code:
            existing = await CompanyService.get_by_code(db, update_data["code"])
            if existing and existing.id != company.id:
                raise HTTPException(
                    status_code=400,
                    detail=f"编码 '{update_data['code']}' 已被主体 '{existing.name}' 使用"
                )
        
        # 处理合作日期字符串转 date 对象
        if "cooperation_date" in update_data and update_data["cooperation_date"]:
            try:
                from datetime import date
                update_data["cooperation_date"] = date.fromisoformat(update_data["cooperation_date"])
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"合作日期格式错误: '{update_data['cooperation_date']}'，应为 YYYY-MM-DD 格式"
                )
        
        for field, value in update_data.items():
            setattr(company, field, value)
        
        await db.commit()
        await db.refresh(company)
        return company
    
    @staticmethod
    async def delete(db: AsyncSession, company: Company) -> None:
        """删除主体（软删除：标记为不活跃）"""
        company.is_active = False
        await db.commit()
    
    @staticmethod
    async def hard_delete(db: AsyncSession, company: Company) -> None:
        """硬删除主体"""
        await db.delete(company)
        await db.commit()
