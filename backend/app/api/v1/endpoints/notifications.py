from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Notification
from app.schemas.notification import NotificationResponse, NotificationListResponse

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """获取通知列表"""
    query = select(Notification)
    count_query = select(func.count(Notification.id))
    
    if unread_only:
        query = query.where(~Notification.is_read)
        count_query = count_query.where(~Notification.is_read)
    
    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return NotificationListResponse(
        total=total,
        items=[NotificationResponse.model_validate(item) for item in items],
        skip=skip,
        limit=limit,
    )


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
):
    """获取未读通知数量（小铃铛用）"""
    result = await db.execute(
        select(func.count(Notification.id)).where(~Notification.is_read)
    )
    count = result.scalar()
    return {"count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
):
    """标记通知为已读"""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在"
        )
    
    notification.is_read = True
    notification.read_at = datetime.now()
    await db.commit()
    await db.refresh(notification)
    
    return NotificationResponse.model_validate(notification)


@router.post("/read-all", response_model=dict)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
):
    """标记所有通知为已读"""
    result = await db.execute(
        select(Notification).where(~Notification.is_read)
    )
    notifications = result.scalars().all()
    
    now = datetime.now()
    for n in notifications:
        n.is_read = True
        n.read_at = now
    
    await db.commit()
    return {"marked_count": len(notifications)}
