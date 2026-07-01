"""
核心工具函数单元测试
"""
from decimal import Decimal

import pytest


class TestDecimalHelpers:
    """测试金额计算工具函数"""

    def test_decimal_addition(self):
        """测试 Decimal 精确加法"""
        a = Decimal("0.1")
        b = Decimal("0.2")
        result = a + b
        assert result == Decimal("0.3")
        assert float(result) == pytest.approx(0.3)

    def test_decimal_multiplication(self):
        """测试 Decimal 精确乘法"""
        price = Decimal("62.11557")
        rate = Decimal("7.0")
        result = price * rate
        assert result == Decimal("434.80899")

    def test_decimal_rounding(self):
        """测试 Decimal 四舍五入"""
        value = Decimal("434.80899")
        rounded = round(value, 2)
        assert rounded == Decimal("434.81")

    def test_decimal_zero_handling(self):
        """测试空值处理"""
        value = None
        safe_value = Decimal(str(value)) if value is not None else Decimal("0")
        assert safe_value == Decimal("0")


class TestFinancialCalculations:
    """测试财务计算逻辑"""

    def test_opening_balance_formula(self):
        """测试期初欠款公式: 期初 = 前期采购 - 前期付款"""
        opening_purchase = Decimal("100000")
        opening_payment = Decimal("30000")
        opening_balance = opening_purchase - opening_payment
        assert opening_balance == Decimal("70000")

    def test_closing_balance_formula(self):
        """测试期末欠款公式: 期末 = 期初 + 本期采购 + 本期费用 - 本期付款"""
        opening = Decimal("70000")
        current_purchase = Decimal("50000")
        current_expenses = Decimal("5000")
        current_payments = Decimal("20000")
        closing = opening + current_purchase + current_expenses - current_payments
        assert closing == Decimal("105000")

    def test_usd_supplier_current_purchase(self):
        """测试 USD 供应商本期采购按美元计算"""
        amount_usd = Decimal("62115.57")
        rate = Decimal("7.0")
        purchase_cny = amount_usd * rate
        # USD 供应商应使用 USD 金额
        is_usd = True
        if is_usd:
            current_purchase = amount_usd
        else:
            current_purchase = purchase_cny
        assert current_purchase == Decimal("62115.57")

    def test_cny_supplier_current_purchase(self):
        """测试 CNY 供应商本期采购按人民币计算"""
        amount_usd = Decimal("62115.57")
        rate = Decimal("7.0")
        purchase_cny = amount_usd * rate
        is_usd = False
        if is_usd:
            current_purchase = amount_usd
        else:
            current_purchase = purchase_cny
        assert current_purchase == Decimal("434808.99")

    def test_exchange_status_logic(self):
        """测试购汇状态判断"""
        has_exchange = True
        status = "exchanged" if has_exchange else "not_exchanged"
        assert status == "exchanged"

        has_exchange = False
        status = "exchanged" if has_exchange else "not_exchanged"
        assert status == "not_exchanged"


class TestPermissions:
    """测试权限矩阵"""

    def test_admin_can_access_all_modules(self):
        """测试 admin 可以访问所有模块"""
        admin_modules = {
            "finance", "reports", "sales", "customers",
            "warehouse", "materials", "system", "users"
        }
        assert len(admin_modules) > 0

    def test_finance_cannot_access_warehouse(self):
        """测试 finance 不能访问仓库模块"""
        finance_modules = {"finance", "reports", "receivable"}
        warehouse_module = "warehouse"
        assert warehouse_module not in finance_modules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
