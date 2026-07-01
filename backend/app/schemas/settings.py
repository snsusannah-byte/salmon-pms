
from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    """用户资料响应"""
    id: int
    username: str
    email: str
    full_name: str | None = None
    phone: str | None = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """更新用户资料"""
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None


class UserPreferencesResponse(BaseModel):
    """用户偏好设置响应"""
    notify_customs_change: bool = True
    notify_batch_lock: bool = True
    notify_payment: bool = False
    compact_mode: bool = False
    auto_refresh: bool = True

    class Config:
        from_attributes = True


class UserPreferencesUpdate(BaseModel):
    """更新用户偏好设置"""
    notify_customs_change: bool | None = None
    notify_batch_lock: bool | None = None
    notify_payment: bool | None = None
    compact_mode: bool | None = None
    auto_refresh: bool | None = None


class UserSettingsResponse(BaseModel):
    """完整用户设置响应（合并资料和偏好）"""
    profile: UserProfileResponse
    preferences: UserPreferencesResponse


class UserSettingsUpdate(BaseModel):
    """完整更新请求"""
    profile: UserProfileUpdate | None = None
    preferences: UserPreferencesUpdate | None = None


class PasswordUpdate(BaseModel):
    """修改密码"""
    old_password: str
    new_password: str
    confirm_password: str
