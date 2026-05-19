"""
退货模块 API — 三文鱼PMS
"""
import os
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.models import (
    ReturnOrder, ReturnItem, ReturnAttachment,
    ReturnStatus, RefundMethod, ReturnAttachmentType,
    Company, BankAccount, User,
    WholeFishSale, FinishedProductSale,
)
from app.schemas.returns import (
    ReturnOrderCreate, ReturnOrderUpdate, ReturnOrderResponse,
    ReturnOrderListResponse, ReturnOrderSummary,
    ReturnItemCreate, ReturnItemUpdate, ReturnItemResponse,
    ReturnAttachmentResponse, ReturnOrderRefund, ReturnOrderApproval,
    ReturnStatsResponse,
)
from app.services.return_service import ReturnService

router = APIRouter()

# ==================== 文件上传配置 ====================

UPLOAD_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))) / "uploads" / "returns"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
ALLOWED_DOC_TYPES = {"application/pdf", "text/plain", "application/msword",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


# ==================== 辅助函数 ====================

def _get_file_type(mime_type: str) -> ReturnAttachmentType:
    if mime_type in ALLOWED_IMAGE_TYPES:
        return ReturnAttachmentType.IMAGE
    elif mime_type in ALLOWED_VIDEO_TYPES:
        return ReturnAttachmentType.VIDEO
    elif mime_type in ALLOWED_DOC_TYPES:
        return ReturnAttachmentType.DOCUMENT
    # 根据扩展名再判断一次
    elif mime_type.startswith("image/"):
        return ReturnAttachmentType.IMAGE
    elif mime_type.startswith("video/"):
        return ReturnAttachmentType.VIDEO
    else:
        return ReturnAttachmentType.DOCUMENT


async def _build_return_response(db: AsyncSession, order: ReturnOrder) -> ReturnOrderResponse:
    """构建退货单响应"""
    # 获取客户名称
    customer_name = None
    if order.customer_id:
        r = await db.execute(select(Company.name).where(Company.id == order.customer_id))
        customer_name = r.scalar()

    # 获取关联销售单号
    sale_no = None
    if order.whole_fish_sale_id:
        r = await db.execute(select(WholeFishSale.sale_no).where(WholeFishSale.id == order.whole_fish_sale_id))
        sale_no = r.scalar()
    elif order.finished_product_sale_id:
        r = await db.execute(select(FinishedProductSale.sale_no).where(FinishedProductSale.id == order.finished_product_sale_id))
        sale_no = r.scalar()

    # 获取创建人/审批人名称
    created_by_name = None
    approved_by_name = None
    if order.created_by_id:
        r = await db.execute(select(User.full_name).where(User.id == order.created_by_id))
        created_by_name = r.scalar()
    if order.approved_by_id:
        r = await db.execute(select(User.full_name).where(User.id == order.approved_by_id))
        approved_by_name = r.scalar()

    items = [ReturnItemResponse.model_validate(i) for i in (order.items or [])]
    attachments = []
    for att in (order.attachments or []):
        att_dict = {
            "id": att.id,
            "return_order_id": att.return_order_id,
            "file_type": att.file_type,
            "original_name": att.original_name,
            "file_name": att.file_name,
            "file_path": att.file_path,
            "file_size": att.file_size,
            "mime_type": att.mime_type,
            "description": att.description,
            "created_at": att.created_at,
            "download_url": f"/api/v1/returns/attachments/{att.file_name}",
        }
        attachments.append(ReturnAttachmentResponse.model_validate(att_dict))

    return ReturnOrderResponse(
        id=order.id,
        return_no=order.return_no,
        sale_no=sale_no,
        sale_type=order.sale_type,
        whole_fish_sale_id=order.whole_fish_sale_id,
        finished_product_sale_id=order.finished_product_sale_id,
        return_date=order.return_date,
        customer_id=order.customer_id,
        processing_plant_id=order.processing_plant_id,
        processing_plant_name=order.processing_plant_name,
        processing_plant_eu_no=order.processing_plant_eu_no,
        total_weight_kg=order.total_weight_kg,
        total_quantity=order.total_quantity,
        total_amount=order.total_amount,
        refund_method=order.refund_method,
        refund_amount=order.refund_amount,
        refund_date=order.refund_date,
        bank_account_id=order.bank_account_id,
        transaction_id=order.transaction_id,
        status=order.status,
        problem_description=order.problem_description,
        customer_feedback=order.customer_feedback,
        internal_notes=order.internal_notes,
        created_by_id=order.created_by_id,
        approved_by_id=order.approved_by_id,
        approved_at=order.approved_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
        attachments=attachments,
    )


# ==================== 退货单 CRUD ====================

@router.get("", response_model=ReturnOrderListResponse)
async def list_returns(
    sale_type: Optional[str] = Query(None, description="销售类型: whole_fish/finished_product"),
    customer_id: Optional[int] = Query(None, description="客户ID"),
    processing_plant_id: Optional[int] = Query(None, description="加工厂ID"),
    status: Optional[ReturnStatus] = Query(None, description="退货单状态"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    search: Optional[str] = Query(None, description="搜索退货单号/客户/问题描述"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """退货单列表"""
    items, total = await ReturnService.list_return_orders(
        db=db,
        sale_type=sale_type,
        customer_id=customer_id,
        processing_plant_id=processing_plant_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
    )
    result_items = []
    for order in items:
        result_items.append(await _build_return_response(db, order))
    return ReturnOrderListResponse(total=total, items=result_items, skip=skip, limit=limit)


@router.post("", response_model=ReturnOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    data: ReturnOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建退货单"""
    # TODO: 从认证中获取当前用户ID
    created_by_id = None
    payload = data.model_dump()
    order = await ReturnService.create_return_order(db, payload, created_by_id)
    return await _build_return_response(db, order)


@router.get("/{return_id}", response_model=ReturnOrderResponse)
async def get_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
):
    """退货单详情"""
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")
    return await _build_return_response(db, order)


@router.put("/{return_id}", response_model=ReturnOrderResponse)
async def update_return(
    return_id: int,
    data: ReturnOrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新退货单（仅草稿/待审批状态）"""
    from app.api.v1.endpoints.sales import _check_batch_locked
    from app.models import WholeFishSale, FinishedProductSale
    
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")
    
    # 检查关联销售单的批次是否锁定
    if order.whole_fish_sale_id:
        await _check_batch_locked(db, sale_id=order.whole_fish_sale_id)
    elif order.finished_product_sale_id:
        sale = await db.get(FinishedProductSale, order.finished_product_sale_id)
        if sale and sale.batch_id:
            await _check_batch_locked(db, batch_id=sale.batch_id)
    
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    updated = await ReturnService.update_return_order(db, order, update_data)
    return await _build_return_response(db, updated)


@router.delete("/{return_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除退货单（仅草稿/已取消状态）"""
    from app.api.v1.endpoints.sales import _check_batch_locked
    from app.models import WholeFishSale, FinishedProductSale
    
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")
    
    # 检查关联销售单的批次是否锁定
    if order.whole_fish_sale_id:
        await _check_batch_locked(db, sale_id=order.whole_fish_sale_id)
    elif order.finished_product_sale_id:
        sale = await db.get(FinishedProductSale, order.finished_product_sale_id)
        if sale and sale.batch_id:
            await _check_batch_locked(db, batch_id=sale.batch_id)
    
    await ReturnService.delete_return_order(db, order)
    return None


# ==================== 审批流程 ====================

@router.post("/{return_id}/submit", response_model=ReturnOrderResponse)
async def submit_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
):
    """提交退货单审批"""
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")
    updated = await ReturnService.submit_for_approval(db, order)
    return await _build_return_response(db, updated)


@router.post("/{return_id}/approve", response_model=ReturnOrderResponse)
async def approve_return(
    return_id: int,
    data: ReturnOrderApproval,
    db: AsyncSession = Depends(get_db),
):
    """审批退货单"""
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")
    approved_by_id = None  # TODO: 从认证获取
    if data.approved:
        updated = await ReturnService.approve(db, order, approved_by_id, data.notes)
    else:
        updated = await ReturnService.reject(db, order, approved_by_id, data.notes)
    return await _build_return_response(db, updated)


@router.post("/{return_id}/refund", response_model=ReturnOrderResponse)
async def refund_return(
    return_id: int,
    data: ReturnOrderRefund,
    db: AsyncSession = Depends(get_db),
):
    """执行退款"""
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")
    processed_by_id = None  # TODO: 从认证获取
    updated = await ReturnService.process_refund(db, order, data, processed_by_id)
    return await _build_return_response(db, updated)


@router.post("/{return_id}/cancel", response_model=ReturnOrderResponse)
async def cancel_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
):
    """取消退货单"""
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")
    updated = await ReturnService.cancel(db, order)
    return await _build_return_response(db, updated)


@router.post("/{return_id}/revert", response_model=ReturnOrderResponse)
async def revert_return(
    return_id: int,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """撤销已完成/退款中的退货单，打回草稿"""
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")
    updated = await ReturnService.revert_completed(db, order, notes)
    return await _build_return_response(db, updated)


# ==================== 附件管理 ====================

@router.post("/{return_id}/attachments", response_model=ReturnAttachmentResponse)
async def upload_attachment(
    return_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """上传附件"""
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")

    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过{MAX_FILE_SIZE // 1024 // 1024}MB限制")

    # 检查文件类型
    mime_type = file.content_type or "application/octet-stream"
    file_type = _get_file_type(mime_type)

    # 生成存储文件名
    ext = Path(file.filename or "unknown").suffix.lower()
    if not ext:
        ext = ".bin"
    store_name = f"{return_id}_{uuid.uuid4().hex[:12]}{ext}"
    sub_dir = date.today().strftime("%Y%m")
    save_dir = UPLOAD_DIR / sub_dir
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / store_name

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建记录
    rel_path = f"returns/{sub_dir}/{store_name}"
    attachment = await ReturnService.add_attachment(db, return_id, {
        "file_type": file_type.value,
        "original_name": file.filename or "unknown",
        "file_name": store_name,
        "file_path": rel_path,
        "file_size": len(content),
        "mime_type": mime_type,
        "description": description,
    })

    return ReturnAttachmentResponse(
        id=attachment.id,
        return_order_id=attachment.return_order_id,
        file_type=attachment.file_type,
        original_name=attachment.original_name,
        file_name=attachment.file_name,
        file_path=attachment.file_path,
        file_size=attachment.file_size,
        mime_type=attachment.mime_type,
        description=attachment.description,
        created_at=attachment.created_at,
        download_url=f"/api/v1/returns/attachments/{store_name}",
    )


@router.get("/attachments/{file_name}")
async def download_attachment(file_name: str):
    """下载附件"""
    # 在 uploads/returns/ 下查找文件
    for sub_dir in UPLOAD_DIR.iterdir():
        if sub_dir.is_dir():
            file_path = sub_dir / file_name
            if file_path.exists():
                from fastapi.responses import FileResponse
                return FileResponse(
                    path=file_path,
                    filename=file_name,
                    media_type="application/octet-stream",
                )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")


@router.delete("/{return_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    return_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除附件"""
    order = await ReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退货单不存在")

    attachment = None
    for att in (order.attachments or []):
        if att.id == attachment_id:
            attachment = att
            break
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="附件不存在")

    # 删除物理文件
    file_path = UPLOAD_DIR / attachment.file_path.replace("returns/", "")
    if file_path.exists():
        file_path.unlink()

    await ReturnService.delete_attachment(db, attachment)
    return None


# ==================== 统计报表 ====================

@router.get("/stats/summary", response_model=dict)
async def get_return_stats(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    sale_type: Optional[str] = Query(None, description="销售类型"),
    db: AsyncSession = Depends(get_db),
):
    """退货综合统计"""
    stats = await ReturnService.get_stats(db, start_date, end_date, sale_type)
    return stats


# ==================== 关联销售单的退货列表 ====================

@router.get("/by-sale/{sale_type}/{sale_id}", response_model=List[ReturnOrderSummary])
async def list_returns_by_sale(
    sale_type: str,
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取某销售单的所有退货单（用于销售单详情页）"""
    if sale_type == "whole_fish":
        result = await db.execute(
            select(ReturnOrder).where(ReturnOrder.whole_fish_sale_id == sale_id)
            .order_by(desc(ReturnOrder.return_date))
        )
    elif sale_type == "finished_product":
        result = await db.execute(
            select(ReturnOrder).where(ReturnOrder.finished_product_sale_id == sale_id)
            .order_by(desc(ReturnOrder.return_date))
        )
    else:
        raise HTTPException(status_code=400, detail="销售类型必须是 whole_fish 或 finished_product")

    orders = result.scalars().all()
    summaries = []
    for order in orders:
        summaries.append(ReturnOrderSummary.model_validate(order))
    return summaries
