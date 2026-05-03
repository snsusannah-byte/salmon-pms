from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    """通知响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    type: str
    title: str
    content: Optional[str] = None
    related_type: Optional[str] = None
    related_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    total: int
    items: list[NotificationResponse]
    skip: int
    limit: int
