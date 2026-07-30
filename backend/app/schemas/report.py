"""
报表中心 Schema
包含：批次财报、单票财报、应收/应付对账单、三大财务报表
"""
from datetime import date
from decimal import Decimal

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
    exchange_rate: Decimal | None = None
    total_exchange_payment: Decimal = Decimal("0")
    total_exchange_fee: Decimal = Decimal("0")
    is_exchange_estimated: bool = False

    # 销售
    total_sales_amount: Decimal = Decimal("0")
    total_sales_net: Decimal = Decimal("0")
    total_sales_weight: Decimal = Decimal("0")
    sales_count: int = 0
    total_commission: Decimal = Decimal("0")

    # 利润
    total_expenses: Decimal = Decimal("0")
    total_other_expenses: Decimal = Decimal("0")
    shrinkage: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    profit_margin: Decimal | None = None
    cumulative_profit: Decimal = Decimal("0")

    # 锁定状态
    is_locked: bool = False


class BatchReportListResponse(BaseModel):
    """批次财报列表响应"""
    total: int
    items: list[BatchReportSummaryItem]
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
    processing_plant_name: str | None = None
    processing_plant_eu_code: str | None = None
    processing_plant_customs_code: str | None = None
    processing_plant_coc_no: str | None = None
    fish_farm_name: str | None = None
    fish_farm_ggn: str | None = None
    fish_farm_coc_no: str | None = None
    fish_farm_area: str | None = None
    exporter_name: str | None = None
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
    products: list[InvoiceProductItem] = []


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
    clearance_extra_items: list[dict] = Field(default_factory=list)

    # 购汇总明
    exchange_rate: Decimal | None = None
    total_exchange_payment: Decimal = Decimal("0")
    total_exchange_fee: Decimal = Decimal("0")
    is_exchange_estimated: bool = False

    # 销售汇总
    total_sales_amount: Decimal = Decimal("0")
    total_sales_net: Decimal = Decimal("0")
    total_sales_weight: Decimal = Decimal("0")
    total_scan_fee: Decimal = Decimal("0")
    total_rounding: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    total_after_sales: Decimal = Decimal("0")
    total_discount: Decimal = Decimal("0")
    total_balance_adjustment: Decimal = Decimal("0")
    sales_count: int = 0

    # 利润
    total_expenses: Decimal = Decimal("0")
    total_other_expenses: Decimal = Decimal("0")
    shrinkage: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    profit_margin: Decimal | None = None

    # 累计利润（需要后端计算）
    cumulative_profit: Decimal = Decimal("0")

    # 锁定状态
    is_locked: bool = False

    # 明细
    invoices: list[BatchReportInvoiceDetail] = []
    sales: list[dict] = []
    other_expenses: list[dict] = []


# ==================== 单票财报 ====================

class InvoiceReportSummaryItem(BaseModel):
    """单票财报列表项"""
    model_config = ConfigDict(from_attributes=True)
    invoice_id: int
    invoice_no: str
    invoice_date: date
    processing_plant_name: str | None = None
    exporter_name: str | None = None
    supplier_name: str | None = None  # 供应商（真正的付款对象）
    batch_name: str | None = None
    batch_code: str | None = None

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
    exchange_rate: Decimal | None = None
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
    profit_margin: Decimal | None = None


class InvoiceReportListResponse(BaseModel):
    """单票财报列表响应"""
    total: int
    items: list[InvoiceReportSummaryItem]
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
    customer_name: str | None = None
    spec: str | None = None
    box_count: int | None = None
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
    kill_date: date | None = None
    arrival_date: date | None = None
    processing_plant_name: str | None = None
    processing_plant_eu_code: str | None = None
    processing_plant_customs_code: str | None = None
    processing_plant_coc_no: str | None = None
    fish_farm_name: str | None = None
    fish_farm_ggn: str | None = None
    fish_farm_coc_no: str | None = None
    fish_farm_area: str | None = None
    exporter_name: str | None = None
    supplier_name: str | None = None
    awb_no: str | None = None
    gross_weight_kg: Decimal | None = None
    batch_name: str | None = None
    batch_code: str | None = None

    # 采购
    total_amount_usd: Decimal = Decimal("0")
    purchase_cost_cny: Decimal = Decimal("0")
    total_weight_kg: Decimal = Decimal("0")
    total_boxes: int = 0

    # 产品明细
    products: list[InvoiceProductDetail] = []

    # 税费
    import_duty: Decimal = Decimal("0")
    import_vat: Decimal = Decimal("0")
    total_taxes: Decimal = Decimal("0")

    # 清关
    clearance_cost: Decimal = Decimal("0")
    clearance_breakdown: dict = Field(default_factory=dict)

    # 购汇
    exchange_rate: Decimal | None = None
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
    sales: list[InvoiceSaleDetail] = []

    # 利润
    total_expenses: Decimal = Decimal("0")
    shrinkage: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    cumulative_profit: Decimal = Decimal("0")
    profit_margin: Decimal | None = None

    # 合并批次销售分摊比例 (0~1, 单票批次为 1)
    sales_proportion: Decimal | None = None


# ==================== 应收款对账单 ====================

class ReceivableSaleItem(BaseModel):
    """应收对账 - 销售明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    sale_no: str
    product_name: str | None = None  # 产品名称
    batch_name: str | None = None      # 批次名称
    slaughter_date: date | None = None  # 宰杀日期（批次关联发票中最早）
    processing_plant_code: str | None = None  # 加工厂EU编号
    spec: str | None = None
    quantity: int | None = None
    weight_kg: Decimal | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal = Decimal("0")
    after_sales_adjustment: Decimal = Decimal("0")  # 售后扣减
    discount: Decimal = Decimal("0")  # 折扣
    net_amount: Decimal = Decimal("0")


class PayablePurchaseItem(BaseModel):
    """应付对账 - 采购明细（进口采购用）"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    invoice_no: str
    product_name: str | None = None  # 产品名称
    spec: str | None = None          # 规格
    batch_no: str | None = None      # 批次号
    quantity: int | None = None      # 数量
    weight_kg: Decimal | None = None # 重量(kg)
    unit_price: Decimal | None = None # 单价
    amount_usd: Decimal = Decimal("0")
    exchange_rate: Decimal | None = None
    amount_cny: Decimal = Decimal("0")
    after_sales_adjustment: Decimal = Decimal("0")  # 采购售后扣减
    # 进口商信息（仅进口采购用）
    importer_name: str | None = None  # 进口商名称
    # 购汇关联信息
    exchange_status: str | None = None  # not_exchanged / exchanged / partial
    exchange_no: str | None = None  # 购汇单号
    exchange_date: date | None = None  # 购汇日期
    exchange_rate_actual: Decimal | None = None  # 实际购汇汇率
    amount_usd_exchanged: Decimal | None = None  # 已购汇 USD 金额


class ReceivableDiscountItem(BaseModel):
    """应收对账 - 折扣明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    sale_no: str
    discount_amount: Decimal = Decimal("0")
    reason: str | None = None


class ReceivableAftersalesItem(BaseModel):
    """应收对账 - 售后明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    return_no: str | None = None  # 退货单号
    sale_no: str | None = None  # 关联销售单号
    quantity: float | None = None  # 退货数量（重量kg）
    unit_price: Decimal | None = None  # 单价
    amount: Decimal = Decimal("0")  # 退款金额
    reason: str | None = None  # 退货原因/备注
    refund_method: str | None = None  # 退款方式


class ReceivableReceiptItem(BaseModel):
    """应收对账 - 收款明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    amount: Decimal = Decimal("0")
    payment_method: str | None = None
    reference_no: str | None = None
    is_batch_collect: bool = False  # 是否合并收款
    related_sales: list[dict] = []  # 关联销售单 [{sale_no, amount, payable_amount}]


class ReceivableCustomerItem(BaseModel):
    """客户应收明细项（单笔销售/收款/售后/折扣）"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    type: str  # "sale_wf" / "sale_fp" / "receipt_wf" / "receipt_fp" / "opening" / "aftersales" / "discount"
    sale_no: str | None = None
    description: str | None = None
    debit: Decimal = Decimal("0")  # 应收增加（销售）
    credit: Decimal = Decimal("0")  # 应收减少（收款/售后/折扣）
    balance: Decimal = Decimal("0")  # 累计余额
    # 销售明细
    spec: str | None = None
    quantity: int | None = None  # 箱数/份数
    weight_kg: Decimal | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal | None = None  # 销售金额（折扣前）
    # 售后明细
    aftersales_reason: str | None = None
    # 折扣
    discount_amount: Decimal | None = None


class ReceivableStatementItem(BaseModel):
    """应收款对账单 - 按客户汇总"""
    model_config = ConfigDict(from_attributes=True)
    customer_id: int
    customer_name: str
    customer_code: str | None = None

    # 汇总
    opening_balance: Decimal = Decimal("0")  # 期初欠款
    current_sales: Decimal = Decimal("0")  # 本期销售（gross_amount）
    current_net_sales: Decimal = Decimal("0")  # 本期净额（net_amount 汇总）
    current_receipts: Decimal = Decimal("0")  # 本期收支
    current_aftersales: Decimal = Decimal("0")  # 本期售后扣减
    current_discount: Decimal = Decimal("0")  # 本期折扣
    closing_balance: Decimal = Decimal("0")  # 期末欠款

    # 明细（兼容旧版前端）
    details: list[ReceivableCustomerItem] = []

    # 分组明细（新版）
    sale_details: list[ReceivableSaleItem] = []
    discount_details: list[ReceivableDiscountItem] = []
    aftersales_details: list[ReceivableAftersalesItem] = []
    receipt_details: list[ReceivableReceiptItem] = []


class ReceivableStatementResponse(BaseModel):
    """应收款对账单响应"""
    total: int
    items: list[ReceivableStatementItem]
    skip: int
    limit: int
    start_date: str | None = None
    end_date: str | None = None
    total_receivable: Decimal = Decimal("0")  # 总应收


# ==================== 应付款对账单 ====================

class PayableSupplierItem(BaseModel):
    """供应商应付明细项"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    type: str  # "invoice" / "payment" / "exchange" / "opening"
    invoice_no: str | None = None
    description: str | None = None
    debit: Decimal = Decimal("0")  # 应付增加（采购/费用）
    credit: Decimal = Decimal("0")  # 应付减少（付款）
    balance: Decimal = Decimal("0")  # 累计余额


class NettingPaymentItem(BaseModel):
    """往来对账 - 收支明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    description: str | None = None
    amount: Decimal = Decimal("0")
    type: str | None = None  # "receipt" / "payment"
    notes: str | None = None


class PayableExchangeItem(BaseModel):
    """应付对账 - 购汇明细（进口采购付款用）"""
    model_config = ConfigDict(from_attributes=True)
    exchange_no: str | None = None  # 购汇单号
    exchange_date: date | None = None  # 购汇日期
    exchange_rate: Decimal | None = None  # 汇率
    amount_usd: Decimal = Decimal("0")  # 购汇金额(USD)
    fee_cny: Decimal = Decimal("0")  # 手续费(CNY)
    amount_cny: Decimal = Decimal("0")  # 购汇金额(CNY)
    total_cny: Decimal = Decimal("0")  # 合计 CNY = amount_cny + fee_cny
    invoice_nos: str | None = None  # 关联发票号列表


class PayableExpenseItem(BaseModel):
    """应付对账 - 费用明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    invoice_no: str | None = None
    expense_type: str  # "import_duty" / "import_vat" / "clearance_fee" / "freight_fee" / "inspection_fee" / "quarantine_fee" / "other"
    description: str | None = None
    amount: Decimal = Decimal("0")
    # 报关行费用细项
    gross_weight_kg: Decimal | None = None  # 出关毛重(kg)
    freight_fee: Decimal | None = None    # 运费
    inspection_fee: Decimal | None = None  # 目的地查验费
    quarantine_fee: Decimal | None = None   # 冷藏费
    other_costs: Decimal | None = None      # 其他费用(报关服务费+提货费等)
    clearance_fee: Decimal | None = None    # 清关费(提货费)
    total_cost: Decimal | None = None       # 清关费合计


class PayablePaymentItem(BaseModel):
    """应付对账 - 付款明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    payment_type: str  # "exchange" / "clearance_payment" / "other"
    amount: Decimal = Decimal("0")
    reference_no: str | None = None
    description: str | None = None


class PayableStatementItem(BaseModel):
    """应付款对账单 - 按供应商汇总"""
    model_config = ConfigDict(from_attributes=True)
    supplier_id: int
    supplier_name: str
    supplier_type: str  # "processing_plant" / "exporter" / "customs_broker" / "logistics"
    supplier_code: str | None = None

    # 汇总
    opening_balance: Decimal = Decimal("0")  # 期初欠款
    current_purchase: Decimal = Decimal("0")  # 本期采购
    current_expenses: Decimal = Decimal("0")  # 本期费用（税费+清关）
    current_payments: Decimal = Decimal("0")  # 本期付款（购汇+其他）
    closing_balance: Decimal = Decimal("0")  # 期末欠款

    # 进口采购汇总（仅进口采购用）
    total_import_usd: Decimal = Decimal("0")  # 进口总金额 USD
    total_exchanged_usd: Decimal = Decimal("0")  # 已购汇金额 USD
    total_unexchanged_usd: Decimal = Decimal("0")  # 未购汇金额 USD
    total_exchanged_cny: Decimal = Decimal("0")  # 已购汇合计 CNY

    # 明细（兼容旧版前端）
    details: list[PayableSupplierItem] = []

    # 分组明细（新版）
    purchase_details: list[PayablePurchaseItem] = []
    expense_details: list[PayableExpenseItem] = []
    payment_details: list[PayablePaymentItem] = []
    exchange_details: list[PayableExchangeItem] = []  # 购汇明细（进口采购用）


class PayableStatementResponse(BaseModel):
    """应付款对账单响应"""
    total: int
    items: list[PayableStatementItem]
    skip: int
    limit: int
    start_date: str | None = None
    end_date: str | None = None
    total_payable: Decimal = Decimal("0")  # 总应付
    purchase_type: str | None = None  # import / domestic / all


class PayableMonthlyItem(BaseModel):
    """供应商月份对账单"""
    model_config = ConfigDict(from_attributes=True)
    month: str  # "2026-03"
    month_label: str  # "2026年3月"
    opening_balance: Decimal = Decimal("0")
    current_purchase: Decimal = Decimal("0")
    current_expenses: Decimal = Decimal("0")
    current_payments: Decimal = Decimal("0")
    closing_balance: Decimal = Decimal("0")
    details: list[PayableSupplierItem] = []


class PayableMonthlyResponse(BaseModel):
    """供应商月份对账单响应"""
    model_config = ConfigDict(from_attributes=True)
    supplier_id: int
    supplier_name: str
    supplier_code: str | None = None
    currency: str = "CNY"
    start_date: str | None = None
    end_date: str | None = None
    total_payable: Decimal = Decimal("0")
    months: list[PayableMonthlyItem] = []


class FinancialStatementItem(BaseModel):
    """财务报表行项目"""
    model_config = ConfigDict(from_attributes=True)
    label: str
    amount: Decimal | None = None
    is_header: bool = False
    is_section: bool = False
    is_subtotal: bool = False
    is_total: bool = False
    is_highlight: bool = False
    is_deduction: bool = False
    is_spacer: bool = False
    indent: int = 0
    note: str | None = None


class IncomeStatement(BaseModel):
    """利润表"""
    model_config = ConfigDict(from_attributes=True)
    title: str = "利润表"
    subtitle: str = "（未经审计）"
    items: list[FinancialStatementItem] = []
    summary: dict = Field(default_factory=dict)


class BalanceSheet(BaseModel):
    """资产负债表"""
    model_config = ConfigDict(from_attributes=True)
    title: str = "资产负债表"
    subtitle: str = "（未经审计）"
    items: list[FinancialStatementItem] = []
    summary: dict = Field(default_factory=dict)
    customer_debts: list[dict] = Field(default_factory=dict)  # TOP5欠款客户


class CashFlowStatement(BaseModel):
    """现金流量表"""
    model_config = ConfigDict(from_attributes=True)
    title: str = "现金流量表"
    subtitle: str = "（未经审计）"
    items: list[FinancialStatementItem] = []
    summary: dict = Field(default_factory=dict)


class FinancialCharts(BaseModel):
    """图表数据"""
    model_config = ConfigDict(from_attributes=True)
    monthly_trend: list[dict] = Field(default_factory=list)
    expense_breakdown: dict = Field(default_factory=dict)
    customer_revenue: list[dict] = Field(default_factory=list)
    profit_trend: list[dict] = Field(default_factory=list)


class NettingStatementItem(BaseModel):
    """往来对账单 - 应收应付综合"""
    model_config = ConfigDict(from_attributes=True)
    company_id: int
    company_name: str
    company_code: str | None = None
    company_type: str | None = None  # customer / supplier / both

    # 应收端
    receivable_opening: Decimal = Decimal("0")
    receivable_current_sales: Decimal = Decimal("0")
    receivable_current_receipts: Decimal = Decimal("0")
    receivable_closing: Decimal = Decimal("0")

    # 应付端
    payable_opening: Decimal = Decimal("0")
    payable_current_purchase: Decimal = Decimal("0")
    payable_current_expenses: Decimal = Decimal("0")
    payable_current_payments: Decimal = Decimal("0")
    payable_closing: Decimal = Decimal("0")

    # 往来净额
    netting_opening: Decimal = Decimal("0")   # 期初应收 - 期初应付
    netting_closing: Decimal = Decimal("0")    # 期末应收 - 期末应付
    netting_direction: str = "平"             # "应收" / "应付" / "平"

    # 分组明细
    sale_details: list[ReceivableSaleItem] = []
    discount_details: list[ReceivableDiscountItem] = []
    aftersales_details: list[ReceivableAftersalesItem] = []
    receipt_details: list[ReceivableReceiptItem] = []
    purchase_details: list[PayablePurchaseItem] = []
    payment_details: list[NettingPaymentItem] = []  # 收支明细
    expense_details: list[PayableExpenseItem] = []
    purchase_return_details: list[dict] = []  # 采购售后明细


class NettingStatementResponse(BaseModel):
    """往来对账单响应"""
    total: int
    items: list[NettingStatementItem]
    skip: int
    limit: int
    start_date: str | None = None
    end_date: str | None = None
    total_net_receivable: Decimal = Decimal("0")  # 总净应收
    total_net_payable: Decimal = Decimal("0")     # 总净应付

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
    start_date: str | None = None
    end_date: str | None = None
    retail_revenue: Decimal = Decimal("0")
    retail_cost: Decimal = Decimal("0")


# ==================== 报关行应付对账单 ====================

class CustomsBrokerFeeItem(BaseModel):
    """报关行费用明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    invoice_no: str
    gross_weight_kg: Decimal = Decimal("0")
    clearance_fee: Decimal = Decimal("0")  # 提货费
    freight_fee: Decimal = Decimal("0")  # 运费
    inspection_fee: Decimal = Decimal("0")  # 目的地查验费
    quarantine_fee: Decimal = Decimal("0")  # 冷藏费
    other_costs: Decimal = Decimal("0")  # 报关服务费
    grand_total: Decimal = Decimal("0")  # 清关费合计
    payment_type: str | None = None


class CustomsBrokerPaymentItem(BaseModel):
    """报关行付款明细"""
    model_config = ConfigDict(from_attributes=True)
    date: date
    amount: Decimal = Decimal("0")
    reference_no: str | None = None
    description: str | None = None
    from_account_name: str | None = None


class CustomsBrokerStatementItem(BaseModel):
    """报关行应付对账单项"""
    model_config = ConfigDict(from_attributes=True)
    broker_id: int
    broker_name: str
    opening_balance: Decimal = Decimal("0")
    current_fees: Decimal = Decimal("0")
    current_payments: Decimal = Decimal("0")
    closing_balance: Decimal = Decimal("0")
    fee_details: list[CustomsBrokerFeeItem] = []
    payment_details: list[CustomsBrokerPaymentItem] = []


class CustomsBrokerStatementResponse(BaseModel):
    """报关行应付对账单响应"""
    total: int
    items: list[CustomsBrokerStatementItem]
    start_date: str | None = None
    end_date: str | None = None
    total_payable: Decimal = Decimal("0")


# ==================== 通用分页参数 ====================

class ReportListRequest(BaseModel):
    """报表列表通用请求"""
    skip: int = 0
    limit: int = 30
    start_date: str | None = None
    end_date: str | None = None
    search: str | None = None
