from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import BatchStatus


class BatchInvoiceInfo(BaseModel):
    """批次中的发票信息"""
    model_config = ConfigDict(from_attributes=True)
    invoice_id: int
    invoice_no: str
    invoice_date: date
    kill_date: date | None = None
    processing_plant_name: str | None = None
    exporter_name: str | None = None
    total_amount_usd: Decimal
    total_boxes: int
    total_weight_kg: Decimal


class BatchBase(BaseModel):
    """批次基础信息"""
    batch_name: str = Field(..., max_length=100, description="批次名称")
    batch_date: date | None = Field(None, description="批次日期")
    notes: str | None = Field(None, description="备注")


class BatchCreate(BaseModel):
    """创建批次请求"""
    batch_code: str | None = Field(None, max_length=50, description="批次编号（留空自动生成）")
    batch_name: str | None = Field(None, max_length=100, description="批次名称（留空自动生成）")
    batch_date: date | None = Field(None, description="批次日期")
    notes: str | None = Field(None, description="备注")
    invoice_ids: list[int] | None = Field(None, description="关联发票ID列表")


class BatchUpdate(BaseModel):
    """更新批次请求"""
    batch_name: str | None = Field(None, max_length=100)
    batch_date: date | None = None
    notes: str | None = None
    status: BatchStatus | None = None


class BatchResponse(BatchBase):
    """批次响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_code: str
    status: BatchStatus
    total_amount_usd: Decimal | None = None
    total_boxes: int = 0
    total_weight_kg: Decimal | None = None
    remaining_boxes: int = 0  # 剩余可用箱数（入库 - 已售）
    invoice_nos: str = ""  # 关联发票号，如 8353&8468
    invoice_count: int = 0
    invoices: list[BatchInvoiceInfo] = []
    slaughter_date: date | None = None  # 关联发票中最早的宰杀日期
    created_at: datetime
    updated_at: datetime


class BatchListResponse(BaseModel):
    """批次列表响应"""
    total: int
    items: list[BatchResponse]
    skip: int
    limit: int


class AddInvoiceToBatch(BaseModel):
    """添加发票到批次"""
    invoice_id: int


class BatchSummary(BaseModel):
    """批次汇总统计"""
    open_count: int
    locked_count: int
    settled_count: int
    total_batches: int
    total_invoices: int
