from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class V4MigrationStatus(BaseModel):
    """V4迁移状态"""
    model_config = ConfigDict(from_attributes=True)
    status: str
    progress: Optional[float] = None
    message: Optional[str] = None
    completed_at: Optional[datetime] = None


class V4MigrationRequest(BaseModel):
    """V4迁移请求"""
    model_config = ConfigDict(from_attributes=True)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    dry_run: bool = True


class V4MigrationResponse(BaseModel):
    """V4迁移响应"""
    model_config = ConfigDict(from_attributes=True)
    success: bool
    records_processed: int = 0
    records_failed: int = 0
    errors: List[str] = []
    summary: Optional[str] = None
