"""
退货模块 Schema — 三文鱼PMS
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import ReturnReason, ReturnStatus, RefundMethod, ReturnAttachmentType


# ==================== ReturnItem 明细（简化版）====================

class ReturnItemBase(BaseModel):
    """退货明细基础（只保留重量、单价、金额）"""
    weight_kg: Decimal = Field(Decimal("0"), ge=Decimal("0"), description="重量(kg)")
    unit_price: Decimal = Field(Decimal("0"), ge=Decimal("0"), description="单价")
    remarks: Optional[str] = Field(None, description="明细备注/问题描述")


class ReturnItemCreate(ReturnItemBase):
    pass


class ReturnItemUpdate(BaseModel):
    weight_kg: Optional[Decimal] = Field(None, ge=Decimal("0"))
    unit_price: Optional[Decimal] = Field(None, ge=Decimal("0"))


class ReturnItemResponse(ReturnItemBase):
    """退货明细响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    return_order_id: int
    amount: Decimal
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==================== ReturnAttachment 附件 ====================

class ReturnAttachmentBase(BaseModel):
    """附件基础"""
    file_type: ReturnAttachmentType = Field(..., description="文件类型")
    original_name: str = Field(..., max_length=255, description="原始文件名")
    file_size: int = Field(0, ge=0, description="文件大小(字节)")
    mime_type: Optional[str] = Field(None, max_length=100, description="MIME类型")
    description: Optional[str] = Field(None, description="文件描述")


class ReturnAttachmentCreate(ReturnAttachmentBase):
    file_name: str = Field(..., max_length=255, description="存储文件名")
    file_path: str = Field(..., max_length=500, description="存储路径")


class ReturnAttachmentResponse(ReturnAttachmentBase):
    """附件响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    return_order_id: int
    file_name: str
    file_path: str
    download_url: Optional[str] = Field(None, description="下载链接")
    created_at: datetime


# ==================== ReturnOrder 退货单 ====================

class ReturnOrderBase(BaseModel):
    """退货单基础"""
    sale_type: str = Field(..., pattern="^(whole_fish|finished_product)$", description="销售类型")
    whole_fish_sale_id: Optional[int] = Field(None, description="整鱼销售单ID")
    finished_product_sale_id: Optional[int] = Field(None, description="成品销售单ID")
    return_date: date = Field(..., description="退货日期")
    customer_id: int = Field(..., description="客户ID")
    processing_plant_id: Optional[int] = Field(None, description="加工厂ID")
    processing_plant_name: Optional[str] = Field(None, max_length=200, description="加工厂名称")
    processing_plant_eu_no: Optional[str] = Field(None, max_length=100, description="加工厂EU注册号")
    problem_description: Optional[str] = Field(None, description="售后问题描述")
    customer_feedback: Optional[str] = Field(None, description="客户反馈")
    internal_notes: Optional[str] = Field(None, description="内部备注")
    refund_method: Optional[RefundMethod] = Field(None, description="退款方式")
    bank_account_id: Optional[int] = Field(None, description="退款银行账户")


class ReturnOrderCreate(ReturnOrderBase):
    items: List[ReturnItemCreate] = Field(..., min_length=1, description="退货明细")


class ReturnOrderUpdate(BaseModel):
    return_date: Optional[date] = None
    customer_id: Optional[int] = None
    processing_plant_id: Optional[int] = None
    processing_plant_name: Optional[str] = Field(None, max_length=200)
    processing_plant_eu_no: Optional[str] = Field(None, max_length=100)
    problem_description: Optional[str] = None
    customer_feedback: Optional[str] = None
    internal_notes: Optional[str] = None
    refund_method: Optional[RefundMethod] = Field(None, description="退款方式")
    bank_account_id: Optional[int] = Field(None, description="退款银行账户")
    items: Optional[List[ReturnItemCreate]] = Field(None, description="替换全部明细（草稿/待审批状态）")


class ReturnOrderRefund(BaseModel):
    """执行退款请求"""
    refund_method: RefundMethod = Field(..., description="退款方式")
    refund_amount: Optional[Decimal] = Field(None, ge=Decimal("0"), description="退款金额（默认=退货总金额）")
    refund_date: Optional[date] = Field(None, description="退款日期（默认=今天）")
    bank_account_id: Optional[int] = Field(None, description="退款银行账户")
    notes: Optional[str] = Field(None, description="退款备注")


class ReturnOrderApproval(BaseModel):
    """审批请求"""
    approved: bool = Field(..., description="是否批准")
    notes: Optional[str] = Field(None, description="审批意见")


class ReturnOrderSummary(BaseModel):
    """退货单摘要（用于销售单详情展示）"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    return_no: str
    sale_no: Optional[str] = Field(None, description="关联销售单号")
    return_date: date
    status: ReturnStatus
    total_weight_kg: Decimal
    total_quantity: int
    total_amount: Decimal
    refund_amount: Decimal
    refund_method: Optional[RefundMethod] = None
    processing_plant_name: Optional[str] = None
    processing_plant_eu_no: Optional[str] = None
    problem_description: Optional[str] = None
    created_at: datetime


class ReturnOrderResponse(ReturnOrderBase):
    """退货单详情响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    return_no: str
    sale_no: Optional[str] = Field(None, description="关联销售单号")
    total_weight_kg: Decimal
    total_quantity: int
    total_amount: Decimal
    refund_method: Optional[RefundMethod] = None
    refund_amount: Decimal
    refund_date: Optional[date] = None
    bank_account_id: Optional[int] = None
    transaction_id: Optional[int] = None
    status: ReturnStatus
    processing_plant_eu_no: Optional[str] = None
    created_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # 关联
    items: List[ReturnItemResponse] = []
    attachments: List[ReturnAttachmentResponse] = []


class ReturnOrderListResponse(BaseModel):
    """退货单列表响应"""
    total: int
    items: List[ReturnOrderResponse]
    skip: int
    limit: int


# ==================== 统计 ====================

class ReturnStatsSummary(BaseModel):
    """退货汇总统计"""
    total_return_orders: int
    total_return_weight_kg: Decimal
    total_return_quantity: int
    total_return_amount: Decimal
    total_refund_amount: Decimal
    pending_count: int
    approved_count: int
    completed_count: int
    rejected_count: int


class ReturnStatsByReason(BaseModel):
    """按退货原因统计"""
    reason: ReturnReason
    reason_label: str
    count: int
    weight_kg: Decimal
    amount: Decimal


class ReturnStatsByPlant(BaseModel):
    """按加工厂统计"""
    processing_plant_id: Optional[int]
    processing_plant_name: str
    count: int
    weight_kg: Decimal
    amount: Decimal


class ReturnStatsByCustomer(BaseModel):
    """按客户统计"""
    customer_id: int
    customer_name: str
    count: int
    weight_kg: Decimal
    amount: Decimal


class ReturnStatsByProduct(BaseModel):
    """按产品统计"""
    product_id: Optional[int]
    product_name: str
    count: int
    weight_kg: Decimal
    amount: Decimal


class ReturnStatsTrendPoint(BaseModel):
    """趋势数据点"""
    period: str  # YYYY-MM-DD or YYYY-MM
    count: int
    weight_kg: Decimal
    amount: Decimal


class ReturnStatsResponse(BaseModel):
    """退货统计综合响应"""
    summary: ReturnStatsSummary
    by_reason: List[ReturnStatsByReason]
    by_plant: List[ReturnStatsByPlant]
    by_customer: List[ReturnStatsByCustomer]
    by_product: List[ReturnStatsByProduct]
    trend: List[ReturnStatsTrendPoint]
