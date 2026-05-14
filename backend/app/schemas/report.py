"""
报表中心 Schema
包含：批次财报、单票财报、应收/应付对账单、三大财务报表
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import BatchStatus


# ==================== 批次财报 ====================

class BatchReportSummaryItem(BaseModel):
    """批次财报列表项"""
    model_config = ConfigDict(from_attributes=True)
    batch_id: int
    batch_code: str
    batch_name: str
    batch_date: date
    status: BatchStatus
    invoice_count: int = 0
    invoice_nos: str = ""

    # 采购
    total_purchase_usd: Decimal = Decimal("0")
    total_purchase_cny: Decimal = Decimal("0")
    total_weight_kg: Decimal = Decimal("0")
    total_boxes: int = 0

    # 税费
    total_import_duty: Decimal = Decimal("0")
    total_import_vat: Decimal = Decimal("0")
    total_taxes: Decimal = Decimal("0")

    # 清关
    total_clearance_cost: Decimal = Decimal("0")

    # 购汇
    exchange_rate: Optional[Decimal] = None
    total_exchange_payment: Decimal = Decimal("0")
    total_exchange_fee: Decimal = Decimal("0")

    # 销售
    total_sales_amount: Decimal = Decimal("0")
    total_sales_net: Decimal = Decimal("0")
    total_sales_weight: Decimal = Decimal("0")
    sales_count: int = 0
    total_commission: Decimal = Decimal("0")

    # 利润
    total_expenses: Decimal = Decimal("0")
    shrinkage: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    profit_margin: Optional[Decimal] = None
    cumulative_profit: Decimal = Decimal("0")

    # 锁定状态
    is_locked: bool = False


class BatchReportListResponse(BaseModel):
    """批次财报列表响应"""
    total: int
    items: List[BatchReportSummaryItem]
    skip: int
    limit: int


class InvoiceProductItem(BaseModel):
    """发票产品明细项"""
    model_config = ConfigDict(from_attributes=True)
    product_name: str
    product_spec: str
    box_count: int
    net_weight_kg: Decimal
    unit_price: Decimal
    total_amount: Decimal


class BatchReportInvoiceDetail(BaseModel):
    """批次财报中发票明细"""
    model_config = ConfigDict(from_attributes=True)
    invoice_id: int
    invoice_no: str
    invoice_date: date
    processing_plant_name: Optional[str] = None
    processing_plant_eu_code: Optional[str] = None
    processing_plant_customs_code: Optional[str] = None
    processing_plant_coc_no: Optional[str] = None
    fish_farm_name: Optional[str] = None
    fish_farm_ggn: Optional[str] = None
    fish_farm_coc_no: Optional[str] = None
    fish_farm_area: Optional[str] = None
    exporter_name: Optional[str] = None
    total_amount_usd: Decimal = Decimal("0")
    total_boxes: int = 0
    total_weight_kg: Decimal = Decimal("0")
    purchase_cost_cny: Decimal = Decimal("0")
    import_duty: Decimal = Decimal("0")
    import_vat: Decimal = Decimal("0")
    clearance_cost: Decimal = Decimal("0")
    exchange_payment: Decimal = Decimal("0")
    exchange_fee: Decimal = Decimal("0")
    sales_net: Decimal = Decimal("0")
    sales_weight: Decimal = Decimal("0")
    shrinkage: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    products: List[InvoiceProductItem] = []


class BatchReportDetail(BaseModel):
    """批次财报详情"""
    model_config = ConfigDict(from_attributes=True)
    batch_id: int
    batch_code: str
    batch_name: str
    batch_date: date
    status: BatchStatus
    invoice_count: int = 0
    invoice_nos: str = ""

    # 采购汇总
    total_purchase_usd: Decimal = Decimal("0")
    total_purchase_cny: Decimal = Decimal("0")
    total_weight_kg: Decimal = Decimal("0")
    total_boxes: int = 0

    # 税费明细
    total_import_duty: Decimal = Decimal("0")
    total_import_vat: Decimal = Decimal("0")
    total_taxes: Decimal = Decimal("0")

    # 清关明细
    total_clearance_cost: Decimal = Decimal("0")
    clearance_breakdown: dict = Field(default_factory=dict)

    # 购汇总明
    exchange_rate: Optional[Decimal] = None
    total_exchange_payment: Decimal = Decimal("0")
    total_exchange_fee: Decimal = Decimal("0")

    # 销售汇总
    total_sales_amount: Decimal = Decimal("0")
    total_sales_net: Decimal = Decimal("0")
    total_sales_weight: Decimal = Decimal("0")
    total_scan_fee: Decimal = Decimal("0")
    total_rounding: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    total_after_sales: Decimal = Decimal("0")
    total_discount: Decimal = Decimal("0")
    sales_count: int = 0

    # 利润
    total_expenses: Decimal = Decimal("0")
    shrinkage: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    profit_margin: Optional[Decimal] = None

    # 累计利润（需要后端计算）
    cumulative_profit: Decimal = Decimal("0")

    # 锁定状态
    is_locked: bool = False

    # 明细
    invoices: List[BatchReportInvoiceDetail] = []
    sales: List[dict] = []


# ==================== 单票财报 ====================

class InvoiceReportSummaryItem(BaseModel):
    """单票财报列表项"""
    model_config = ConfigDict(from_attributes=True)
    invoice_id: int
    invoice_no: str
    invoice_date: date
    processing_plant_name: Optional[str] = None
    exporter_name: Optional[str] = None
    supplier_name: Optional[str] = None  # 供应商（真正的付款对象）
    batch_name: Optional[str] = None
    batch_code: Optional[str] = None

    # 采购
    total_amount_usd: Decimal = Decimal("0")
    purchase_cost_cny: Decimal = Decimal("0")
    total_weight_kg: Decimal = Decimal("0")
    total_boxes: int = 0

    # 税费
    import_duty: Decimal = Decimal("0")
    import_vat: Decimal = Decimal("0")
    total_taxes: Decimal = Decimal("0")

    # 清关
    clearance_cost: Decimal = Decimal("0")

    # 购汇
    exchange_rate: Optional[Decimal] = None
    exchange_payment: Decimal = Decimal("0")
    exchange_fee: Decimal = Decimal("0")

    # 销售
    sales_net: Decimal = Decimal("0")
    sales_weight: Decimal = Decimal("0")
    sales_count: int = 0

    # 利润
    total_expenses: Decimal = Decimal("0")
    shrinkage: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    profit_margin: Optional[Decimal] = None


class InvoiceReportListResponse(BaseModel):
    """单票财报列表响应"""
    total: int
    items: List[InvoiceReportSummaryItem]
    skip: int
    limit: int


class InvoiceProductDetail(BaseModel):
    """发票产品明细"""
    model_config = ConfigDict(from_attributes=True)
    product_name: str
    product_spec: str
    box_count: int
    net_weight_kg: Decimal
    unit_price: Decimal
    total_amount: Decimal


class InvoiceSaleDetail(BaseModel):
    """发票销售明细"""
    model_config = ConfigDict(from_attributes=True)
    sale_date: date
    customer_name: Optional[str] = None
    spec: Optional[str] = None
    box_count: Optional[int] = None
    weight_kg: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    gross_amount: Decimal = Decimal("0")
    scan_fee: Decimal = Decimal("0")
    rounding_adjustment: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    after_sales_adjustment: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")


class InvoiceReportDetail(BaseModel):
    """单票财报详情"""
    model_config = ConfigDict(from_attributes=True)
    invoice_id: int
    invoice_no: str
    invoice_date: date
    kill_date: Optional[date] = None
    arrival_date: Optional[date] = None
    processing_plant_name: Optional[str] = None
    processing_plant_eu_code: Optional[str] = None
    processing_plant_customs_code: Optional[str] = None
    processing_plant_coc_no: Optional[str] = None
    fish_farm_name: Optional[str] = None
    fish_farm_ggn: Optional[str] = None
    fish_farm_coc_no: Optional[str] = None
    fish_farm_area: Optional[str] = None
    exporter_name: Optional[str] = None
    supplier_name: Optional[str] = None
    awb_no: Optional[str] = None
    gross_weight_kg: Optional[Decimal] = None
    batch_name: Optional[str] = None
    batch_code: Optional[str] = None

    # 采购
    total_amount_usd: Decimal = Decimal("0")
    purchase_cost_cny: Decimal = Decimal("0")
    total_weight_kg: Decimal = Decimal("0")
    total_boxes: int = 0

    # 产品明细
    products: List[InvoiceProductDetail] = []

    # 税费
    import_duty: Decimal = Decimal("0")
    import_vat: Decimal = Decimal("0")
    total_taxes: Decimal = Decimal("0")

    # 清关
    clearance_cost: Decimal = Decimal("0")
    clearance_breakdown: dict = Field(default_factory=dict)

    # 购汇
    exchange_rate: Optional[Decimal] = None
    exchange_payment: Decimal = Decimal("0")
    exchange_fee: Decimal = Decimal("0")

    # 销售
    total_sales_amount: Decimal = Decimal("0")
    total_sales_net: Decimal = Decimal("0")
    total_sales_weight: Decimal = Decimal("0")
    total_scan_fee: Decimal = Decimal("0")
    total_rounding: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    total_after_sales: Decimal = Decimal("0")
    total_discount: Decimal = Decimal("0")
    sales_count: int = 0
    sales: List[InvoiceSaleDetail] = []

    # 利润
    total_expenses: Decimal = Decimal("0")
    shrinkage: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    cumulative_profit: Decimal = Decimal("0")
    profit_margin: Optional[Decimal] = None


# ==================== 应收款对账单 ====================

class ReceivableCustomerItem(BaseModel):
    """客户应收明细项（单笔销售/收款）"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    type: str  # "sale" / "receipt" / "opening"
    sale_no: Optional[str] = None
    description: Optional[str] = None
    debit: Decimal = Decimal("0")  # 应收增加（销售）
    credit: Decimal = Decimal("0")  # 应收减少（收款）
    balance: Decimal = Decimal("0")  # 累计余额


class ReceivableStatementItem(BaseModel):
    """应收款对账单 - 按客户汇总"""
    model_config = ConfigDict(from_attributes=True)
    customer_id: int
    customer_name: str
    customer_code: Optional[str] = None

    # 汇总
    opening_balance: Decimal = Decimal("0")  # 期初欠款
    current_sales: Decimal = Decimal("0")  # 本期销售
    current_receipts: Decimal = Decimal("0")  # 本期收款
    current_aftersales: Decimal = Decimal("0")  # 本期售后扣减
    closing_balance: Decimal = Decimal("0")  # 期末欠款

    # 明细
    details: List[ReceivableCustomerItem] = []


class ReceivableStatementResponse(BaseModel):
    """应收款对账单响应"""
    total: int
    items: List[ReceivableStatementItem]
    skip: int
    limit: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_receivable: Decimal = Decimal("0")  # 总应收


# ==================== 应付款对账单 ====================

class PayableSupplierItem(BaseModel):
    """供应商应付明细项"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    type: str  # "invoice" / "payment" / "exchange" / "opening"
    invoice_no: Optional[str] = None
    description: Optional[str] = None
    debit: Decimal = Decimal("0")  # 应付增加（采购/费用）
    credit: Decimal = Decimal("0")  # 应付减少（付款）
    balance: Decimal = Decimal("0")  # 累计余额


class PayableStatementItem(BaseModel):
    """应付款对账单 - 按供应商汇总"""
    model_config = ConfigDict(from_attributes=True)
    supplier_id: int
    supplier_name: str
    supplier_type: str  # "processing_plant" / "exporter" / "customs_broker" / "logistics"
    supplier_code: Optional[str] = None

    # 汇总
    opening_balance: Decimal = Decimal("0")  # 期初欠款
    current_purchase: Decimal = Decimal("0")  # 本期采购
    current_expenses: Decimal = Decimal("0")  # 本期费用（税费+清关）
    current_payments: Decimal = Decimal("0")  # 本期付款（购汇+其他）
    closing_balance: Decimal = Decimal("0")  # 期末欠款

    # 明细
    details: List[PayableSupplierItem] = []


class PayableStatementResponse(BaseModel):
    """应付款对账单响应"""
    total: int
    items: List[PayableStatementItem]
    skip: int
    limit: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_payable: Decimal = Decimal("0")  # 总应付


# ==================== 三大财务报表 ====================

class FinancialStatementItem(BaseModel):
    """财务报表行项目"""
    model_config = ConfigDict(from_attributes=True)
    label: str
    amount: Optional[Decimal] = None
    is_header: bool = False
    is_section: bool = False
    is_subtotal: bool = False
    is_total: bool = False
    is_highlight: bool = False
    is_deduction: bool = False
    is_spacer: bool = False
    indent: int = 0
    note: Optional[str] = None


class IncomeStatement(BaseModel):
    """利润表"""
    model_config = ConfigDict(from_attributes=True)
    title: str = "利润表"
    subtitle: str = "（未经审计）"
    items: List[FinancialStatementItem] = []
    summary: dict = Field(default_factory=dict)


class BalanceSheet(BaseModel):
    """资产负债表"""
    model_config = ConfigDict(from_attributes=True)
    title: str = "资产负债表"
    subtitle: str = "（未经审计）"
    items: List[FinancialStatementItem] = []
    summary: dict = Field(default_factory=dict)
    customer_debts: List[dict] = Field(default_factory=dict)  # TOP5欠款客户


class CashFlowStatement(BaseModel):
    """现金流量表"""
    model_config = ConfigDict(from_attributes=True)
    title: str = "现金流量表"
    subtitle: str = "（未经审计）"
    items: List[FinancialStatementItem] = []
    summary: dict = Field(default_factory=dict)


class FinancialCharts(BaseModel):
    """图表数据"""
    model_config = ConfigDict(from_attributes=True)
    monthly_trend: List[dict] = Field(default_factory=list)
    expense_breakdown: dict = Field(default_factory=dict)
    customer_revenue: List[dict] = Field(default_factory=list)
    profit_trend: List[dict] = Field(default_factory=list)


class FinancialStatements(BaseModel):
    """三大财务报表完整数据"""
    model_config = ConfigDict(from_attributes=True)
    meta: dict = Field(default_factory=dict)
    income_statement: IncomeStatement = Field(default_factory=IncomeStatement)
    balance_sheet: BalanceSheet = Field(default_factory=BalanceSheet)
    cash_flow: CashFlowStatement = Field(default_factory=CashFlowStatement)
    charts: FinancialCharts = Field(default_factory=FinancialCharts)


class FinancialStatementsRequest(BaseModel):
    """三大报表请求参数"""
    period_type: str = "current_quarter"  # current_quarter / last_quarter / first_half / second_half / current_year / last_year / custom
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    retail_revenue: Decimal = Decimal("0")
    retail_cost: Decimal = Decimal("0")


# ==================== 通用分页参数 ====================

class ReportListRequest(BaseModel):
    """报表列表通用请求"""
    skip: int = 0
    limit: int = 30
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    search: Optional[str] = None
