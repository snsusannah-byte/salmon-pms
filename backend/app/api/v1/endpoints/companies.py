
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import log_operation, require_admin
from app.models import BankAccount, CompanyType, CustomerCategory, Salesperson, SupplierCategory, User
from app.schemas.company import (
    BankAccountItem,
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
    get_business_role,
)
from app.services.company_service import CompanyService

router = APIRouter()


async def _sync_company_bank_accounts(
    db: AsyncSession,
    company: Any,
    accounts: list[BankAccountItem],
) -> None:
    """同步公司的收款银行账户列表

    规则：以传入列表为准，无 ID 则新建，有 ID 则更新，列表中未包含的现有账户删除。
    """
    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(BankAccount).where(BankAccount.company_id == company.id)
    )
    existing = {acc.id: acc for acc in result.scalars().all()}

    kept_ids = set()
    for item in accounts:
        # 过滤空账户（允许用户预留空行）
        if not item.account_name or not item.bank_name or not item.account_number:
            continue
        if item.id and item.id in existing:
            acc = existing[item.id]
            acc.account_name = item.account_name
            acc.bank_name = item.bank_name
            acc.account_number = item.account_number
            acc.currency = item.currency or acc.currency
            acc.is_active = item.is_active if item.is_active is not None else acc.is_active
            acc.notes = item.notes
            kept_ids.add(item.id)
        else:
            new_acc = BankAccount(
                company_id=company.id,
                account_name=item.account_name,
                bank_name=item.bank_name,
                account_number=item.account_number,
                currency=item.currency or "CNY",
                is_active=item.is_active if item.is_active is not None else True,
                notes=item.notes,
                code=uuid4().hex[:12],
                type="public",
                opening_balance=0,
                current_balance=0,
            )
            db.add(new_acc)
            await db.flush()
            kept_ids.add(new_acc.id)

    for acc_id, acc in existing.items():
        if acc_id not in kept_ids:
            await db.delete(acc)

    await db.commit()
    await db.refresh(company)


async def _build_company_response(db: AsyncSession, company, payables: dict = None) -> CompanyResponse:
    """构建主体响应（含业务员名称、应付款）"""
    salesperson_name = None
    if company.salesperson_id:
        r = await db.execute(select(Salesperson.name).where(Salesperson.id == company.salesperson_id))
        salesperson_name = r.scalar()
    
    payable = payables.get(company.id) if payables else None
    
    data = {
        "id": company.id,
        "name": company.name,
        "chinese_name": company.chinese_name,
        "company_full_name": company.company_full_name,
        "brands": company.brands,
        "type": company.type,
        "code": company.code,
        "cooperation_date": company.cooperation_date.isoformat() if company.cooperation_date else None,
        "contact_person": company.contact_person,
        "phone": company.phone,
        "email": company.email,
        "address": company.address,
        "registration_code": company.registration_code,
        "enterprise_registration_no": company.enterprise_registration_no,
        "coc_cert_no": company.coc_cert_no,
        "farming_area": company.farming_area,
        "website": company.website,
        "bank_name": company.bank_name,
        "bank_account": company.bank_account,
        "payee": company.payee,
        "currency": company.currency,
        "credit_limit": company.credit_limit,
        "logistics_info": company.logistics_info,
        "salesperson_id": company.salesperson_id,
        "customer_category": company.customer_category.value if company.customer_category else None,
        "customer_level": company.customer_level,
        "supplier_category": company.supplier_category if company.supplier_category else None,
        "prepaid_balance": company.prepaid_balance,
        "customer_type": company.customer_type,
        "is_internal": company.is_internal,
        "is_active": company.is_active,
        "notes": company.notes,
        "salesperson_name": salesperson_name,
        "business_role": get_business_role(company.type.value if hasattr(company.type, 'value') else str(company.type)),
        "payable_usd": payable["payable_usd"] if payable else None,
        "payable_cny": payable["payable_cny"] if payable else None,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
    }
    if hasattr(company, "bank_accounts"):
        data["bank_accounts"] = [
            {
                "id": acc.id,
                "account_name": acc.account_name,
                "bank_name": acc.bank_name,
                "account_number": acc.account_number,
                "currency": acc.currency,
                "is_active": acc.is_active,
                "notes": acc.notes,
            }
            for acc in (company.bank_accounts or [])
        ]
    return CompanyResponse(**data)


@router.get("/", response_model=CompanyListResponse)
async def list_companies(
    type: CompanyType | None = Query(None, description="主体类型"),
    exclude_type: list[CompanyType] = Query([], description="排除类型（可传多个，如 customer,supplier）"),
    business_role: str | None = Query(None, description="业务角色筛选：upstream(上游溯源) / business_partner(业务往来)"),
    supplier_category: SupplierCategory | None = Query(None, description="供应商分类筛选：raw_material/material_supply/customs_broker/service_provider/importer"),
    customer_category: CustomerCategory | None = Query(None, description="客户分类筛选：wholesaler/distributor/retailer/platform/group_buying"),
    search: str | None = Query(None, description="搜索关键词"),
    is_active: bool | None = Query(True, description="是否启用"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """主体列表
    
    - **type**: 按类型筛选（加工厂/渔场/出口商/供应商/客户等）
    - **exclude_type**: 排除指定类型列表（如排除 customer,supplier）
    - **business_role**: 按业务角色筛选（upstream=上游溯源，business_partner=业务往来）
    - **supplier_category**: 按供应商分类筛选（raw_material/material_supply/customs_broker/service_provider/importer）
    - **customer_category**: 按客户分类筛选（wholesaler/distributor/retailer/platform/group_buying）
    - **search**: 按名称/编码/联系人搜索
    - **is_active**: 是否只显示启用中的主体
    """
    items, total = await CompanyService.list_companies(
        db=db,
        type=type,
        exclude_type=exclude_type,
        business_role=business_role,
        supplier_category=supplier_category,
        customer_category=customer_category,
        search=search,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    
    supplier_ids = [item.id for item in items if hasattr(item.type, 'value') and item.type.value == "supplier"]
    payables = await CompanyService.get_supplier_payables(db, supplier_ids)
    
    result_items = []
    for item in items:
        result_items.append(await _build_company_response(db, item, payables))
    
    return CompanyListResponse(total=total, items=result_items, skip=skip, limit=limit)


@router.post("/batch-import", status_code=status.HTTP_201_CREATED)
async def batch_import_customers(
    customers: list[dict],
    db: AsyncSession = Depends(get_db),
):
    """批量导入客户（销售导入用）
    
    去重规则：按名称匹配，已存在则更新空字段，不存在则创建。
    返回：{created: 新增数, updated: 更新数, items: 客户列表}
    """
    created_count = 0
    updated_count = 0
    result_items = []
    
    for customer_data in customers:
        name = customer_data.get("name", "").strip()
        if not name:
            continue
            
        customer = await CompanyService.get_or_create_customer(
            db=db,
            name=name,
            contact_person=customer_data.get("contact_person"),
            phone=customer_data.get("phone"),
            address=customer_data.get("address"),
            customer_category=customer_data.get("customer_category"),
        )
        
        # 判断是否新创建
        if customer.created_at == customer.updated_at or not customer.created_at:
            created_count += 1
        else:
            updated_count += 1
            
        result_items.append(await _build_company_response(db, customer))
    
    return {
        "created": created_count,
        "updated": updated_count,
        "items": result_items,
    }


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建主体"""
    company = await CompanyService.create(db, data)
    if data.bank_accounts:
        await _sync_company_bank_accounts(db, company, data.bank_accounts)
    return await _build_company_response(db, company)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    """主体详情"""
    company = await CompanyService.get_by_id(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"主体 ID={company_id} 不存在",
        )
    return await _build_company_response(db, company)


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新主体"""
    company = await CompanyService.get_by_id(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"主体 ID={company_id} 不存在",
        )
    
    # 检查编码是否与其他主体冲突
    if data.code and data.code != company.code:
        existing = await CompanyService.get_by_code(db, data.code)
        if existing and existing.id != company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"主体编码 '{data.code}' 已被其他主体使用",
            )
    
    updated = await CompanyService.update(db, company, data)
    if data.bank_accounts is not None:
        await _sync_company_bank_accounts(db, updated, data.bank_accounts)
    return await _build_company_response(db, updated)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: int,
    hard: bool = Query(False, description="是否硬删除（仅限管理员）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """删除主体
    
    - 默认软删除（标记 is_active=false）
    - hard=true 时硬删除（从数据库中移除）—— 仅限管理员
    """
    company = await CompanyService.get_by_id(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"主体 ID={company_id} 不存在",
        )
    
    if hard:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"硬删除主体: ID={company_id}, name={company.name}, code={company.code}, by={user.username}")
        await log_operation(db, user.id, "hard_delete", "companies", "Company", company_id, f"硬删除 {company.name}")
        await CompanyService.hard_delete(db, company)
    else:
        await CompanyService.delete(db, company)
    
    return None
