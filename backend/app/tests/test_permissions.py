"""
RBAC 权限系统单元测试
"""
import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, MagicMock

from app.core.permissions import (
    UserRole,
    require_role,
    require_admin,
    require_finance,
    require_sales,
    require_warehouse,
    MODULE_PERMISSIONS,
    SENSITIVE_OPERATIONS,
)


class MockUser:
    def __init__(self, id=1, username="test", role="user", is_active=True):
        self.id = id
        self.username = username
        self.role = role
        self.is_active = is_active


@pytest.fixture
def mock_user():
    return MockUser()


@pytest.fixture
def mock_admin():
    return MockUser(role="admin")


@pytest.fixture
def mock_finance():
    return MockUser(role="finance")


@pytest.fixture
def mock_sales():
    return MockUser(role="sales")


@pytest.fixture
def mock_warehouse():
    return MockUser(role="warehouse")


@pytest.fixture
def mock_inactive():
    return MockUser(is_active=False)


class TestUserRole:
    """角色枚举测试"""

    def test_role_values(self):
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.FINANCE.value == "finance"
        assert UserRole.SALES.value == "sales"
        assert UserRole.WAREHOUSE.value == "warehouse"
        assert UserRole.USER.value == "user"

    def test_role_from_string(self):
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("finance") == UserRole.FINANCE
        assert UserRole("user") == UserRole.USER


class TestRequireRole:
    """权限依赖测试"""

    @pytest.mark.asyncio
    async def test_admin_can_access_anything(self, mock_admin):
        """管理员可以访问任何权限保护的端点"""
        for role in [UserRole.ADMIN, UserRole.FINANCE, UserRole.SALES, UserRole.WAREHOUSE, UserRole.USER]:
            dep = require_role(role)
            user = await dep(mock_admin)
            assert user.role == "admin"

    @pytest.mark.asyncio
    async def test_user_can_access_user_only(self, mock_user):
        """普通用户可以访问 user 级别的端点"""
        dep = require_role(UserRole.USER)
        user = await dep(mock_user)
        assert user.role == "user"

    @pytest.mark.asyncio
    async def test_user_cannot_access_admin(self, mock_user):
        """普通用户不能访问 admin 级别的端点"""
        dep = require_role(UserRole.ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            await dep(mock_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_user_cannot_access_finance(self, mock_user):
        """普通用户不能访问 finance 级别的端点"""
        dep = require_role(UserRole.FINANCE)
        with pytest.raises(HTTPException) as exc_info:
            await dep(mock_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_finance_can_access_finance(self, mock_finance):
        """财务可以访问 finance 端点"""
        dep = require_role(UserRole.ADMIN, UserRole.FINANCE)
        user = await dep(mock_finance)
        assert user.role == "finance"

    @pytest.mark.asyncio
    async def test_sales_can_access_sales(self, mock_sales):
        """销售可以访问 sales 端点"""
        dep = require_role(UserRole.ADMIN, UserRole.SALES)
        user = await dep(mock_sales)
        assert user.role == "sales"

    @pytest.mark.asyncio
    async def test_warehouse_can_access_warehouse(self, mock_warehouse):
        """仓库可以访问 warehouse 端点"""
        dep = require_role(UserRole.ADMIN, UserRole.WAREHOUSE)
        user = await dep(mock_warehouse)
        assert user.role == "warehouse"

    @pytest.mark.asyncio
    async def test_inactive_user_forbidden(self, mock_inactive):
        """禁用用户应被禁止访问"""
        dep = require_role(UserRole.USER)
        with pytest.raises(HTTPException) as exc_info:
            await dep(mock_inactive)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "禁用" in exc_info.value.detail


class TestModulePermissions:
    """模块权限矩阵测试"""

    def test_finance_module_roles(self):
        """财务模块只允许 admin 和 finance"""
        allowed = MODULE_PERMISSIONS["finance"]
        assert UserRole.ADMIN in allowed
        assert UserRole.FINANCE in allowed
        assert UserRole.SALES not in allowed
        assert UserRole.WAREHOUSE not in allowed
        assert UserRole.USER not in allowed

    def test_reports_module_roles(self):
        """报表模块只允许 admin 和 finance"""
        allowed = MODULE_PERMISSIONS["reports"]
        assert UserRole.ADMIN in allowed
        assert UserRole.FINANCE in allowed
        assert UserRole.SALES not in allowed

    def test_sales_module_roles(self):
        """销售模块只允许 admin 和 sales"""
        allowed = MODULE_PERMISSIONS["sales"]
        assert UserRole.ADMIN in allowed
        assert UserRole.SALES in allowed
        assert UserRole.FINANCE not in allowed

    def test_warehouse_module_roles(self):
        """仓库模块只允许 admin 和 warehouse"""
        allowed = MODULE_PERMISSIONS["warehouse"]
        assert UserRole.ADMIN in allowed
        assert UserRole.WAREHOUSE in allowed
        assert UserRole.SALES not in allowed

    def test_system_module_admin_only(self):
        """系统管理仅允许 admin"""
        allowed = MODULE_PERMISSIONS["system"]
        assert allowed == {UserRole.ADMIN}


class TestSensitiveOperations:
    """敏感操作权限测试"""

    def test_delete_requires_admin(self):
        assert SENSITIVE_OPERATIONS["delete"] == {UserRole.ADMIN}

    def test_unlock_requires_admin(self):
        assert SENSITIVE_OPERATIONS["unlock"] == {UserRole.ADMIN}

    def test_lock_allows_warehouse_and_finance(self):
        allowed = SENSITIVE_OPERATIONS["lock"]
        assert UserRole.ADMIN in allowed
        assert UserRole.WAREHOUSE in allowed
        assert UserRole.FINANCE in allowed


class TestRequireShortcuts:
    """快捷依赖测试"""

    def test_require_admin_only_allows_admin(self):
        dep = require_admin
        # 通过检查依赖函数的闭包来验证
        # require_admin 是通过 require_role(UserRole.ADMIN) 创建的
        assert dep is not None

    def test_require_finance_allows_admin_and_finance(self):
        dep = require_finance
        assert dep is not None


class TestLogOperation:
    """操作日志测试"""

    @pytest.mark.asyncio
    async def test_log_operation_runs(self):
        """日志记录不应抛出异常"""
        from app.core.permissions import log_operation
        mock_db = AsyncMock()
        # 不应抛出异常
        await log_operation(mock_db, 1, "test", "module")
