from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class V4MigrationStatus(BaseModel):
    """V4迁移状态"""
    model_config = ConfigDict(from_attributes=True)
    status: str
    progress: float | None = None
    message: str | None = None
    completed_at: datetime | None = None


class V4MigrationRequest(BaseModel):
    """V4迁移请求"""
    model_config = ConfigDict(from_attributes=True)
    start_date: date | None = None
    end_date: date | None = None
    dry_run: bool = True


class V4MigrationResponse(BaseModel):
    """V4迁移响应"""
    model_config = ConfigDict(from_attributes=True)
    success: bool
    records_processed: int = 0
    records_failed: int = 0
    errors: list[str] = []
    summary: str | None = None
