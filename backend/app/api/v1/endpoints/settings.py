from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_password, get_password_hash
from app.models import User, UserSettings
from app.schemas.settings import (
    UserSettingsResponse,
    UserSettingsUpdate,
    PasswordUpdate,
    UserProfileResponse,
    UserPreferencesResponse,
)

router = APIRouter()


async def _get_or_create_settings(db: AsyncSession, user_id: int) -> UserSettings:
    """获取或创建用户设置"""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/me", response_model=UserSettingsResponse)
async def get_my_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户完整设置"""
    settings = await _get_or_create_settings(db, user.id)
    return UserSettingsResponse(
        profile=UserProfileResponse.model_validate(user),
        preferences=UserPreferencesResponse.model_validate(settings),
    )


@router.put("/me", response_model=UserSettingsResponse)
async def update_my_settings(
    data: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户设置"""
    # 更新用户资料
    if data.profile:
        if data.profile.full_name is not None:
            user.full_name = data.profile.full_name
        if data.profile.email is not None:
            # 检查邮箱是否已被其他用户使用
            if data.profile.email != user.email:
                result = await db.execute(
                    select(User).where(
                        User.email == data.profile.email,
                        User.id != user.id,
                    )
                )
                if result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="邮箱已被其他用户使用",
                    )
            user.email = data.profile.email
        if data.profile.phone is not None:
            user.phone = data.profile.phone

    # 更新偏好设置
    if data.preferences:
        settings = await _get_or_create_settings(db, user.id)
        for field in [
            "notify_customs_change",
            "notify_batch_lock",
            "notify_payment",
            "compact_mode",
            "auto_refresh",
        ]:
            value = getattr(data.preferences, field, None)
            if value is not None:
                setattr(settings, field, value)

    await db.commit()
    await db.refresh(user)

    settings = await _get_or_create_settings(db, user.id)
    return UserSettingsResponse(
        profile=UserProfileResponse.model_validate(user),
        preferences=UserPreferencesResponse.model_validate(settings),
    )


@router.post("/me/password")
async def change_password(
    data: PasswordUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户密码"""
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的新密码不一致",
        )

    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )

    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    return {"success": True, "message": "密码修改成功"}
