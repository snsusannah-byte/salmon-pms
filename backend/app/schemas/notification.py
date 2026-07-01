from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    """通知响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    type: str
    title: str
    content: str | None = None
    related_type: str | None = None
    related_id: int | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    total: int
    items: list[NotificationResponse]
    skip: int
    limit: int
