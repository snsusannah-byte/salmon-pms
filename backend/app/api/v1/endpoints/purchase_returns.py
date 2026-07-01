"""采购售后/退货模块 API — 三文鱼PMS

参考销售退货单（returns.py），但方向相反：
- 销售退货：退钱给客户
- 采购售后：抵扣应付款 / 供应商退钱
"""
import os
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    Company,
    PurchaseOrderV2,
    PurchaseReturnAttachment,
    PurchaseReturnOrder,
    PurchaseReturnStatus,
    User,
)
from app.services.purchase_return_service import PurchaseReturnService

router = APIRouter()

# ==================== 文件上传配置 ====================

UPLOAD_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))) / "uploads" / "purchase_returns"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
ALLOWED_DOC_TYPES = {"application/pdf", "text/plain", "application/msword",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def _get_file_type(mime_type: str):
    from app.models.purchase_returns import PurchaseReturnAttachmentType
    if mime_type in ALLOWED_IMAGE_TYPES:
        return PurchaseReturnAttachmentType.IMAGE
    elif mime_type in ALLOWED_VIDEO_TYPES:
        return PurchaseReturnAttachmentType.VIDEO
    elif mime_type in ALLOWED_DOC_TYPES:
        return PurchaseReturnAttachmentType.DOCUMENT
    elif mime_type.startswith("image/"):
        return PurchaseReturnAttachmentType.IMAGE
    elif mime_type.startswith("video/"):
        return PurchaseReturnAttachmentType.VIDEO
    else:
        return PurchaseReturnAttachmentType.DOCUMENT


async def _build_response(db: AsyncSession, order: PurchaseReturnOrder) -> dict:
    """构建采购售后单响应"""
    # 获取供应商名称
    supplier_name = order.supplier_name or ""
    if order.supplier_id:
        r = await db.execute(select(Company.name).where(Company.id == order.supplier_id))
        name = r.scalar()
        if name:
            supplier_name = name

    # 获取关联采购单号
    purchase_no = None
    if order.purchase_order_v2_id:
        r = await db.execute(select(PurchaseOrderV2.purchase_no).where(PurchaseOrderV2.id == order.purchase_order_v2_id))
        purchase_no = r.scalar()

    items = []
    for item in (order.items or []):
        items.append({
            "id": item.id,
            "weight_kg": float(item.weight_kg) if item.weight_kg else 0,
            "unit_price": float(item.unit_price) if item.unit_price else 0,
            "amount": float(item.amount) if item.amount else 0,
            "remarks": item.remarks,
            "purchase_order_product_v2_id": item.purchase_order_product_v2_id,
            "material_purchase_item_id": item.material_purchase_item_id,
        })

    attachments = []
    for att in (order.attachments or []):
        attachments.append({
            "id": att.id,
            "file_type": att.file_type.value if att.file_type else "document",
            "original_name": att.original_name,
            "file_name": att.file_name,
            "file_path": att.file_path,
            "file_size": att.file_size,
            "mime_type": att.mime_type,
            "description": att.description,
            "created_at": att.created_at.isoformat() if att.created_at else None,
            "download_url": f"/api/v1/purchase-returns/attachments/{att.file_name}",
        })

    return {
        "id": order.id,
        "return_no": order.return_no,
        "purchase_no": purchase_no,
        "purchase_order_type": order.purchase_order_type,
        "purchase_order_v2_id": order.purchase_order_v2_id,
        "material_purchase_order_id": order.material_purchase_order_id,
        "return_date": order.return_date.isoformat() if order.return_date else None,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier_name,
        "total_weight_kg": float(order.total_weight_kg) if order.total_weight_kg else 0,
        "total_amount": float(order.total_amount) if order.total_amount else 0,
        "refund_method": order.refund_method.value if order.refund_method else None,
        "refund_amount": float(order.refund_amount) if order.refund_amount else 0,
        "refund_date": order.refund_date.isoformat() if order.refund_date else None,
        "bank_account_id": order.bank_account_id,
        "status": order.status.value if order.status else "draft",
        "problem_description": order.problem_description,
        "supplier_feedback": order.supplier_feedback,
        "internal_notes": order.internal_notes,
        "created_by_id": order.created_by_id,
        "approved_by_id": order.approved_by_id,
        "approved_at": order.approved_at.isoformat() if order.approved_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "items": items,
        "attachments": attachments,
    }


# ==================== 采购单信息查询（用于创建售后单时自动带出） ====================

@router.get("/purchase-order-info")
async def get_purchase_order_info(
    order_type: str = Query(..., description="purchase_v2 或 material_purchase"),
    order_id: int = Query(..., description="采购单ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取采购单信息，用于创建售后单时自动带出单价、供应商等"""
    try:
        info = await PurchaseReturnService.get_purchase_order_for_return(db, order_type, order_id)
        return {
            "supplier_id": info["supplier_id"],
            "supplier_name": info["supplier_name"],
            "total_amount": float(info["total_amount"]),
            "avg_unit_price": float(info["avg_unit_price"]),
            "products": [
                {
                    "id": p.id,
                    "product_name": getattr(p, "product_name", getattr(p, "name", "")),
                    "product_spec": getattr(p, "product_spec", getattr(p, "spec", "")),
                    "weight_kg": float(getattr(p, "weight_kg", getattr(p, "total_qty", 0))),
                    "unit_price": float(getattr(p, "unit_price", getattr(p, "actual_unit_price", 0))),
                    "total_amount": float(getattr(p, "total_amount", getattr(p, "actual_amount", 0))),
                }
                for p in info["products"]
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== 售后单 CRUD ====================

@router.get("")
async def list_purchase_returns(
    purchase_order_type: str | None = Query(None),
    supplier_id: int | None = Query(None),
    status: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """采购售后单列表"""
    items, total = await PurchaseReturnService.list_return_orders(
        db=db,
        purchase_order_type=purchase_order_type,
        supplier_id=supplier_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
    )
    result_items = []
    for order in items:
        result_items.append(await _build_response(db, order))
    return {"total": total, "items": result_items, "skip": skip, "limit": limit}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_purchase_return(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建采购售后单"""
    created_by_id = current_user.id if current_user else None
    order = await PurchaseReturnService.create_return_order(db, data, created_by_id)
    return await _build_response(db, order)


@router.get("/{return_id}")
async def get_purchase_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """采购售后单详情"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")
    return await _build_response(db, order)


@router.put("/{return_id}")
async def update_purchase_return(
    return_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新采购售后单（更新后自动重新计算扣款）"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")

    update_data = {k: v for k, v in data.items() if v is not None}
    updated = await PurchaseReturnService.update_return_order(db, order, update_data)
    return await _build_response(db, updated)


@router.delete("/{return_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除采购售后单（自动回滚扣款）"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")
    await PurchaseReturnService.delete_return_order(db, order)
    return None


# ==================== 审批流程 ====================

@router.post("/{return_id}/submit")
async def submit_purchase_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """提交售后单审批"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")
    updated = await PurchaseReturnService.submit_for_approval(db, order)
    return await _build_response(db, updated)


@router.post("/{return_id}/approve")
async def approve_purchase_return(
    return_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审批售后单"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")
    approved_by_id = current_user.id if current_user else None
    approved = data.get("approved", True)
    notes = data.get("notes")
    if approved:
        updated = await PurchaseReturnService.approve(db, order, approved_by_id, notes)
    else:
        updated = await PurchaseReturnService.reject(db, order, approved_by_id, notes)
    return await _build_response(db, updated)


@router.post("/{return_id}/complete")
async def complete_purchase_return(
    return_id: int,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """完成售后单 — 执行退款/抵扣"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")
    refund_date = data.get("refund_date") if data else None
    if refund_date:
        refund_date = date.fromisoformat(refund_date)
    updated = await PurchaseReturnService.complete(db, order, refund_date)
    return await _build_response(db, updated)


@router.post("/{return_id}/cancel")
async def cancel_purchase_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取消售后单"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")
    updated = await PurchaseReturnService.cancel(db, order)
    return await _build_response(db, updated)


# ==================== 附件管理 ====================

@router.post("/{return_id}/attachments")
async def upload_attachment(
    return_id: int,
    file: UploadFile = File(...),
    description: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """上传附件"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过{MAX_FILE_SIZE // 1024 // 1024}MB限制")

    mime_type = file.content_type or "application/octet-stream"
    file_type = _get_file_type(mime_type)

    ext = Path(file.filename or "unknown").suffix.lower()
    if not ext:
        ext = ".bin"
    store_name = f"{return_id}_{uuid.uuid4().hex[:12]}{ext}"
    sub_dir = date.today().strftime("%Y%m")
    save_dir = UPLOAD_DIR / sub_dir
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / store_name

    with open(file_path, "wb") as f:
        f.write(content)

    rel_path = f"purchase_returns/{sub_dir}/{store_name}"
    attachment = await PurchaseReturnService.add_attachment(db, return_id, {
        "file_type": file_type.value,
        "original_name": file.filename or "unknown",
        "file_name": store_name,
        "file_path": rel_path,
        "file_size": len(content),
        "mime_type": mime_type,
        "description": description,
    })

    return {
        "id": attachment.id,
        "return_order_id": attachment.return_order_id,
        "file_type": attachment.file_type.value if attachment.file_type else "document",
        "original_name": attachment.original_name,
        "file_name": attachment.file_name,
        "file_path": attachment.file_path,
        "file_size": attachment.file_size,
        "mime_type": attachment.mime_type,
        "description": attachment.description,
        "created_at": attachment.created_at.isoformat() if attachment.created_at else None,
        "download_url": f"/api/v1/purchase-returns/attachments/{store_name}",
    }


@router.get("/attachments/{file_name}")
async def download_attachment(file_name: str):
    """下载附件"""
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
    raise HTTPException(status_code=404, detail="文件不存在")


@router.delete("/{return_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    return_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除附件"""
    order = await PurchaseReturnService.get_return_order(db, return_id)
    if not order:
        raise HTTPException(status_code=404, detail="售后单不存在")

    attachment = None
    for att in (order.attachments or []):
        if att.id == attachment_id:
            attachment = att
            break
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    file_path = UPLOAD_DIR / attachment.file_path.replace("purchase_returns/", "")
    if file_path.exists():
        file_path.unlink()

    await PurchaseReturnService.delete_attachment(db, attachment)
    return None
