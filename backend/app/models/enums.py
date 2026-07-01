# ruff: noqa: F821
from enum import StrEnum


class CompanyType(StrEnum):
    PROCESSING_PLANT = "processing_plant"      # 加工厂
    FISH_FARM = "fish_farm"                    # 渔场
    EXPORTER = "exporter"                      # 出口商
    SUPPLIER = "supplier"                      # 供应商
    CUSTOMER = "customer"                      # 客户
    CUSTOMS_BROKER = "customs_broker"          # 报关行
    LOGISTICS = "logistics"                    # 物流
    INTERNAL = "internal"                      # 内部



class InvoiceStatus(StrEnum):
    """报关状态（3态流转）"""
    PENDING_CUSTOMS = "pending_customs"        # 待报关（新建发票默认）
    CUSTOMS_PROCESSING = "customs_processing"  # 已报关（费用录入后）
    CLEARED = "cleared"                        # 已结关（加入批次后）
    # 已弃用状态（兼容旧数据）
    PENDING_SHIPMENT = "pending_shipment"      # 已弃用-映射为待报关
    IN_TRANSIT = "in_transit"                  # 已弃用-映射为已报关
    PICKED_UP = "picked_up"                    # 已弃用-映射为已结关



class ExchangeStatus(StrEnum):
    """购汇状态"""
    NOT_EXCHANGED = "not_exchanged"            # 未购汇
    PARTIAL = "partial"                        # 部分购汇
    COMPLETED = "completed"                    # 全部购汇



class BatchStatus(StrEnum):
    OPEN = "open"                              # 开放
    LOCKED = "locked"                          # 已锁定
    SETTLED = "settled"                        # 已结算



class SalesStatus(StrEnum):
    PENDING = "pending"                        # 待收款
    PARTIAL_PAID = "partial_paid"              # 部分收款
    FULLY_PAID = "fully_paid"                  # 全部收款
    AFTER_SALES = "after_sales"                # 售后中



class TransactionType(StrEnum):
    INCOME = "income"                          # 收入
    EXPENSE = "expense"                        # 支出
    TRANSFER = "transfer"                      # 转账
    EXCHANGE = "exchange"                      # 购汇



class TransactionCategory(StrEnum):
    # === 收入 ===
    MAIN_BUSINESS_REVENUE = "main_business_revenue"       # 主营业务收入（整鱼/成品/副产品）
    OTHER_BUSINESS_REVENUE = "other_business_revenue"     # 其他业务收入（废料）
    NON_BUSINESS_REVENUE = "non_business_revenue"         # 营业外收入（投资/借款/利息）
    FUND_POOLING = "fund_pooling"                         # 资金归集（银行/线上零售）
    CUSTOMER_DEPOSIT = "customer_deposit"                 # 客户预付款

    # === 内部划转 ===
    BALANCE_DEDUCTION = "balance_deduction"               # 余额抵扣销售单

    # === 支出-销售费用 ===
    MARKETING_FEE = "marketing_fee"                         # 市场推广费
    PACKAGING_CONSUMABLES = "packaging_consumables"         # 包装物及低值易耗品
    GIFT_FEE = "gift_fee"                                   # 赠品费用
    SCAN_FEE = "scan_fee"                                   # 扫码手续费
    TRANSPORT_FEE = "transport_fee"                         # 运输装卸费
    SALES_COMMISSION = "sales_commission"                   # 销售佣金

    # === 支出-管理费用 ===
    STAFF_SALARY = "staff_salary"                           # 职工薪酬
    RENT_FEE = "rent_fee"                                   # 租赁费
    OFFICE_FEE = "office_fee"                               # 办公费
    TRAVEL_FEE = "travel_fee"                               # 差旅费
    AGENCY_FEE = "agency_fee"                               # 中介服务费
    DEPRECIATION = "depreciation"                           # 固定资产折旧
    MAINTENANCE_FEE = "maintenance_fee"                    # 维修维护费
    INSURANCE_FEE = "insurance_fee"                         # 保险费
    ENTERTAINMENT_FEE = "entertainment_fee"                 # 业务招待费
    TRAINING_FEE = "training_fee"                         # 培训费

    # === 支出-财务费用 ===
    INTEREST_EXPENSE = "interest_expense"                   # 利息支出
    EXCHANGE_LOSS = "exchange_loss"                         # 汇兑损益
    BANK_FEE = "bank_fee"                                   # 银行手续费

    # === 支出-成本支出 ===
    GOODS_PAYMENT = "goods_payment"                         # 货款支付
    TAX_PAYMENT = "tax_payment"                             # 税费支付
    CLEARANCE_PAYMENT = "clearance_payment"                 # 清关费支付
    INTERNATIONAL_FREIGHT = "international_freight"         # 国际运费支付
    SALES_REFUND = "sales_refund"                           # 销售退货退款

    # === 旧分类（兼容已有数据，已废弃）===
    SALES_INCOME = "sales_income"                           # [废弃] 销售收入
    INVESTMENT = "investment"                               # [废弃] 投资款
    LOAN = "loan"                                           # [废弃] 借款
    INTEREST = "interest"                                   # [废弃] 利息收入
    ONLINE_OPERATION = "online_operation"                   # [废弃] 线上运营
    RENT = "rent"                                           # [废弃] 场地租赁
    FIXED_ASSET = "fixed_asset"                             # [废弃] 固定资产
    SALARY = "salary"                                       # [废弃] 工资
    TRAVEL = "travel"                                       # [废弃] 差旅
    LOGISTICS_COST = "logistics_cost"                       # [废弃] 物流费
    CLEARANCE_COST = "clearance_cost"                       # [废弃] 清关费
    OTHER = "other"                                         # [废弃] 其他



class InventoryStatus(StrEnum):
    IN_STOCK = "in_stock"                      # 在库
    RESERVED = "reserved"                      # 预留
    PROCESSING = "processing"                  # 加工中
    SOLD = "sold"                              # 已售



class MovementType(StrEnum):
    INBOUND = "inbound"                        # 入库
    OUTBOUND = "outbound"                      # 出库
    ADJUSTMENT = "adjustment"                  # 调整
    TRANSFER = "transfer"                      # 转移


# ==================== 仓库模块V2 枚举 ====================


class WarehouseType(StrEnum):
    """仓库类型"""
    WHOLE_PACKAGE = "whole_package"   # 整包仓
    SUB_PACKAGE = "sub_package"       # 分包仓
    ACCESSORY = "accessory"           # 辅料仓
    BYPRODUCT = "byproduct"           # 副产品仓
    FINISHED = "finished"             # 成品仓



class WarehouseBusinessScope(StrEnum):
    """仓库业务范围"""
    IMPORT = "import"       # 进口单证
    DOMESTIC = "domestic"   # 国内业务
    ALL = "all"             # 通用



class StockStatus(StrEnum):
    """单据状态"""
    PENDING = "pending"     # 待确认
    COMPLETED = "completed" # 已完成
    CANCELLED = "cancelled" # 已取消



class StockMovementType(StrEnum):
    """库存变动类型"""
    INBOUND = "inbound"           # 入库
    OUTBOUND = "outbound"         # 出库
    TRANSFER_IN = "transfer_in"   # 调拨入
    TRANSFER_OUT = "transfer_out" # 调拨出
    ADJUSTMENT = "adjustment"     # 盘点调整


# ==================== 基础层 ====================


class CustomerCategory(StrEnum):
    """客户分类"""
    WHOLESALER = "wholesaler"          # 批发商
    DISTRIBUTOR = "distributor"        # 渠道商
    RETAILER = "retailer"              # 零售商
    PLATFORM = "platform"              # 平台
    GROUP_BUYING = "group_buying"      # 团购



class SupplierCategory(StrEnum):
    """供应商分类"""
    RAW_MATERIAL = "raw_material"          # 原料供应
    MATERIAL_SUPPLY = "material_supply"    # 物料供应
    CUSTOMS_BROKER = "customs_broker"      # 报关行
    SERVICE_PROVIDER = "service_provider"  # 服务商



class PurchaseOrderStatus(StrEnum):
    """采购单状态"""
    PENDING = "pending"           # 待入库
    PARTIAL = "partial"         # 部分入库
    COMPLETED = "completed"     # 已完成
    CANCELLED = "cancelled"     # 已取消


