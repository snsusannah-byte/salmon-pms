"""API 端点测试"""
import pytest


class TestHealthCheck:
    """健康检查端点"""

    def test_docs_accessible(self, client):
        """Swagger UI 可访问"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "Swagger UI" in response.text

    def test_openapi_json(self, client):
        """OpenAPI schema 可访问"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert len(data["paths"]) > 0


class TestAuth:
    """认证相关端点"""

    def test_login_requires_credentials(self, client):
        """未提供凭据返回 422"""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_invalid_credentials(self, client):
        """错误凭据返回 401 或 422（schema 验证）"""
        response = client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "wrong"
        })
        assert response.status_code in (401, 422)


class TestReports:
    """报表端点测试"""

    @pytest.mark.xfail(reason="SQLite 不支持 PostgreSQL 的 TO_CHAR 函数")
    def test_financial_statements_accessible(self, client):
        """财务报表端点可访问"""
        response = client.get("/api/v1/reports/financial-statements?period_type=current_year")
        assert response.status_code == 200
        data = response.json()
        assert "income_statement" in data
        assert "cash_flow" in data
        assert "balance_sheet" in data

    def test_batch_reports_list(self, client):
        """批次财报列表"""
        response = client.get("/api/v1/reports/batches")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_invoice_reports_list(self, client):
        """单票财报列表"""
        response = client.get("/api/v1/reports/invoices")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_payable_statements(self, client):
        """应付款对账单"""
        response = client.get("/api/v1/reports/payable-statements")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_payable" in data
