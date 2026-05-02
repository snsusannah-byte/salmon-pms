from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# ==================== 枚举定义 ====================
class CompanyType(str, PyEnum):
    PROCESSING_PLANT = "processing_plant"      # 加工厂
    FISH_FARM = "fish_farm"                    # 渔场
    EXPORTER = "exporter"                      # 出口商
    SUPPLIER = "supplier"                      # 供应商
    CUSTOMER = "customer"                      # 客户
    CUSTOMS_BROKER = "customs_broker"          # 报关行
    LOGISTICS = "logistics"                    # 物流
    INTERNAL = "internal"                      # 内部


class InvoiceStatus(str, PyEnum):
    """报关状态（清关流程）"""
    PENDING_SHIPMENT = "pending_shipment"      # 待发货
    IN_TRANSIT = "in_transit"                  # 运输中
    PENDING_CUSTOMS = "pending_customs"        # 待报关
    CUSTOMS_PROCESSING = "customs_processing"  # 报关中
    CLEARED = "cleared"                        # 已清关
    PICKED_UP = "picked_up"                    # 已提货


class ExchangeStatus(str, PyEnum):
    """购汇状态"""
    NOT_EXCHANGED = "not_exchanged"            # 未购汇
    PARTIAL = "partial"                        # 部分购汇
    COMPLETED = "completed"                    # 全部购汇


class BatchStatus(str, PyEnum):
    OPEN = "open"                              # 开放
    LOCKED = "locked"                          # 已锁定
    SETTLED = "settled"                        # 已结算


class SalesStatus(str, PyEnum):
    PENDING = "pending"                        # 待收款
    PARTIAL_PAID = "partial_paid"              # 部分收款
    FULLY_PAID = "fully_paid"                  # 全部收款
    AFTER_SALES = "after_sales"                # 售后中


class TransactionType(str, PyEnum):
    INCOME = "income"                          # 收入
    EXPENSE = "expense"                        # 支出
    TRANSFER = "transfer"                      # 转账
    EXCHANGE = "exchange"                      # 购汇


class TransactionCategory(str, PyEnum):
    # 收入
    SALES_INCOME = "sales_income"              # 销售收入
    INVESTMENT = "investment"                  # 投资款
    LOAN = "loan"                              # 借款
    INTEREST = "interest"                      # 利息收入
    # 支出
    ONLINE_OPERATION = "online_operation"      # 线上运营
    RENT = "rent"                              # 场地租赁
    FIXED_ASSET = "fixed_asset"                # 固定资产
    SALARY = "salary"                          # 工资
    TRAVEL = "travel"                          # 差旅
    SCAN_FEE = "scan_fee"                      # 扫码手续费
    TAX = "tax"                                # 税费
    LOGISTICS_COST = "logistics_cost"          # 物流费
    CLEARANCE_COST = "clearance_cost"          # 清关费
    OTHER = "other"                            # 其他


class InventoryStatus(str, PyEnum):
    IN_STOCK = "in_stock"                      # 在库
    RESERVED = "reserved"                      # 预留
    PROCESSING = "processing"                  # 加工中
    SOLD = "sold"                              # 已售


class MovementType(str, PyEnum):
    INBOUND = "inbound"                        # 入库
    OUTBOUND = "outbound"                      # 出库
    ADJUSTMENT = "adjustment"                  # 调整
    TRANSFER = "transfer"                      # 转移


# ==================== 基础层 ====================

class CustomerCategory(str, PyEnum):
    """客户分类"""
    WHOLESALER = "wholesaler"          # 批发商
    DISTRIBUTOR = "distributor"        # 渠道商
    RETAILER = "retailer"              # 零售商
    PLATFORM = "platform"              # 平台
    GROUP_BUYING = "group_buying"      # 团购


class Company(Base, TimestampMixin):
    """主体管理：加工厂/渔场/出口商/供应商/客户/报关行/物流/内部"""
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    chinese_name: Mapped[Optional[str]] = mapped_column(String(200))
    type: Mapped[CompanyType] = mapped_column(Enum(CompanyType), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    cooperation_date: Mapped[Optional[Date]] = mapped_column(Date)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    registration_code: Mapped[Optional[str]] = mapped_column(String(100))
    enterprise_registration_no: Mapped[Optional[str]] = mapped_column(String(100))
    coc_cert_no: Mapped[Optional[str]] = mapped_column(String(100))
    farming_area: Mapped[Optional[str]] = mapped_column(String(100), default="FAO 27")
    website: Mapped[Optional[str]] = mapped_column(String(255))
    bank_name: Mapped[Optional[str]] = mapped_column(String(200))
    bank_account: Mapped[Optional[str]] = mapped_column(String(100))
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    # 客户专用字段
    logistics_info: Mapped[Optional[str]] = mapped_column(Text)  # 物流信息
    salesperson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))  # 业务员
    customer_category: Mapped[Optional[CustomerCategory]] = mapped_column(Enum(CustomerCategory))  # 客户分类
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    salesperson: Mapped["User"] = relationship("User", foreign_keys=[salesperson_id], lazy="raise")


class Salesperson(Base, TimestampMixin):
    """业务员管理"""
    __tablename__ = "salespersons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))  # 默认提成比例 %
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class CommissionRecord(Base, TimestampMixin):
    """提成记录"""
    __tablename__ = "commission_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    salesperson_id: Mapped[int] = mapped_column(ForeignKey("salespersons.id"), nullable=False)
    sale_id: Mapped[int] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=False)
    sale_date: Mapped[Date] = mapped_column(Date, nullable=False)
    sale_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # 销售金额
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # 实际提成比例
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # 提成金额
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / paid
    paid_date: Mapped[Optional[Date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    salesperson: Mapped["Salesperson"] = relationship("Salesperson", lazy="raise")


class BankAccount(Base, TimestampMixin):
    """银行账户管理"""
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class User(Base, TimestampMixin):
    """用户管理"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)


# ==================== 采购层 ====================

class ImportInvoice(Base, TimestampMixin):
    """进口发票（核心表，保持原有编号）"""
    __tablename__ = "import_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_no: Mapped[str] = mapped_column(String(100), nullable=False)       # 发票编号
    invoice_date: Mapped[Date] = mapped_column(Date, nullable=False)           # 发票日期
    kill_date: Mapped[Optional[Date]] = mapped_column(Date)
    arrival_date: Mapped[Optional[Date]] = mapped_column(Date)
    
    processing_plant_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    fish_farm_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"))
    exporter_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    
    total_amount_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_boxes: Mapped[int] = mapped_column(Integer, default=0)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    
    # 物流与证书信息
    awb_no: Mapped[Optional[str]] = mapped_column(String(50))  # AWB航空运单号
    gross_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 毛重(kg)
    eta: Mapped[Optional[DateTime]] = mapped_column(DateTime)  # ETA预计到达
    departure_date: Mapped[Optional[Date]] = mapped_column(Date)  # 发运时间
    flight_info: Mapped[Optional[str]] = mapped_column(String(100))  # 航班信息
    origin_certificate: Mapped[Optional[str]] = mapped_column(String(100))  # 原产地证书
    inspection_certificate: Mapped[Optional[str]] = mapped_column(String(100))  # 检验检疫证书
    
    # 成本相关（V8.2新增）
    unit_price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))  # 采购单价(USD)
    estimated_exchange_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))  # 预估汇率
    estimated_cost_cny: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))  # 预估成本(CNY)
    actual_cost_cny: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))  # 实际成本(CNY)
    
    # 报关状态（清关流程）
    customs_status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING_CUSTOMS)
    # 购汇状态
    exchange_status: Mapped[ExchangeStatus] = mapped_column(Enum(ExchangeStatus), default=ExchangeStatus.NOT_EXCHANGED)
    # 是否锁定（批次结算后锁定）
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    processing_plant: Mapped["Company"] = relationship("Company", foreign_keys=[processing_plant_id])
    fish_farm: Mapped["Company"] = relationship("Company", foreign_keys=[fish_farm_id])
    exporter: Mapped["Company"] = relationship("Company", foreign_keys=[exporter_id])
    products: Mapped[List["InvoiceProduct"]] = relationship("InvoiceProduct", back_populates="invoice", lazy="raise", uselist=True, cascade="all, delete-orphan")


class ProductCategory(str, Enum):
    """产品分类"""
    WHOLE_FISH = "whole_fish"           # 整鱼规格
    FINISHED_PRODUCT = "finished_product"  # 成品定义
    BYPRODUCT = "byproduct"              # 副产品
    BOM_MATERIAL = "bom_material"      # BOM物料/包材


class Product(Base, TimestampMixin):
    """产品档案（统一产品管理）"""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[ProductCategory] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)   # 产品编码
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 产品名称
    spec: Mapped[Optional[str]] = mapped_column(String(100))        # 规格描述 / 规格编码
    unit: Mapped[str] = mapped_column(String(20), default="kg")   # 单位
    unit_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))  # 单位重量(kg)
    # 成品规格专用字段
    series_code: Mapped[Optional[str]] = mapped_column(String(10))      # 系列代号 如A
    series_name: Mapped[Optional[str]] = mapped_column(String(100))    # 系列名称 如三文鱼纯享
    portion_weight_g: Mapped[Optional[int]] = mapped_column(Integer)     # 单份重量(g)
    portion_boxes: Mapped[Optional[int]] = mapped_column(Integer)        # 份内盒数
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # 成品特有的BOM关系
    boms: Mapped[List["ProductBOM"]] = relationship("ProductBOM", 
                                                       foreign_keys="ProductBOM.finished_product_id",
                                                       back_populates="finished_product",
                                                       lazy="raise",
                                                       cascade="all, delete-orphan")


class ProductBOM(Base, TimestampMixin):
    """成品BOM物料清单"""
    __tablename__ = "product_boms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finished_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)  # 用量
    unit: Mapped[str] = mapped_column(String(20), default="个")  # 用量单位
    notes: Mapped[Optional[str]] = mapped_column(Text)

    finished_product: Mapped["Product"] = relationship("Product",
                                                        foreign_keys=[finished_product_id],
                                                        back_populates="boms")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


class ProductPackaging(Base, TimestampMixin):
    """成品包装物清单（盒级/份级）"""
    __tablename__ = "product_packagings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # box:盒级, portion:份级
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)  # 用量
    unit: Mapped[str] = mapped_column(String(20), default="个")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id], lazy="raise")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


class InvoiceProduct(Base, TimestampMixin):
    """发票产品明细"""
    __tablename__ = "invoice_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 产品名称
    product_spec: Mapped[str] = mapped_column(String(100), nullable=False)  # 规格
    box_count: Mapped[int] = mapped_column(Integer, nullable=False)
    net_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    invoice: Mapped["ImportInvoice"] = relationship("ImportInvoice", back_populates="products", lazy="raise")


class Shipment(Base, TimestampMixin):
    """发货批次（物流层）"""
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shipment_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    shipment_date: Mapped[Date] = mapped_column(Date, nullable=False)
    logistics_company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    container_no: Mapped[Optional[str]] = mapped_column(String(50))
    vessel_name: Mapped[Optional[str]] = mapped_column(String(100))
    departure_port: Mapped[Optional[str]] = mapped_column(String(100))
    arrival_port: Mapped[Optional[str]] = mapped_column(String(100))
    eta: Mapped[Optional[Date]] = mapped_column(Date)
    ata: Mapped[Optional[Date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="in_transit")
    notes: Mapped[Optional[str]] = mapped_column(Text)


class Batch(Base, TimestampMixin):
    """批次管理"""
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # 批次编号: YYYYMMDD-NNN
    batch_name: Mapped[str] = mapped_column(String(100), nullable=False)
    batch_date: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[BatchStatus] = mapped_column(Enum(BatchStatus), default=BatchStatus.OPEN)
    total_amount_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    total_boxes: Mapped[int] = mapped_column(Integer, default=0)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    batch_invoices: Mapped[List["BatchInvoice"]] = relationship("BatchInvoice", back_populates="batch", lazy="raise", cascade="all, delete-orphan")


class BatchInvoice(Base, TimestampMixin):
    """批次-发票关联"""
    __tablename__ = "batch_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="batch_invoices", lazy="raise")


# ==================== 财务层 ====================

class ExchangeRecord(Base, TimestampMixin):
    """购汇记录（1张发票支持N条）"""
    __tablename__ = "exchange_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    exchange_date: Mapped[Date] = mapped_column(Date, nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    amount_cny: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    fee_cny: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"))
    status: Mapped[str] = mapped_column(String(20), default="completed")
    notes: Mapped[Optional[str]] = mapped_column(Text)


class ImportTax(Base, TimestampMixin):
    """进口税费"""
    __tablename__ = "import_taxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    tax_date: Mapped[Date] = mapped_column(Date, nullable=False)
    import_duty: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    import_vat: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    consumption_tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    other_taxes: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class ClearanceCost(Base, TimestampMixin):
    """清关运费"""
    __tablename__ = "clearance_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    cost_date: Mapped[Date] = mapped_column(Date, nullable=False)
    clearance_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    freight_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    inspection_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    quarantine_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    other_costs: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ==================== 销售层 ====================

class WholeFishSale(Base, TimestampMixin):
    """整鱼销售"""
    __tablename__ = "whole_fish_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    sale_date: Mapped[Date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    scan_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    rounding_adjustment: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    after_sales_adjustment: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    status: Mapped[SalesStatus] = mapped_column(Enum(SalesStatus), default=SalesStatus.PENDING)
    salesperson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class FinishedProductSale(Base, TimestampMixin):
    """成品销售"""
    __tablename__ = "finished_product_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_date: Mapped[Date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 件数
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    scan_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    status: Mapped[SalesStatus] = mapped_column(Enum(SalesStatus), default=SalesStatus.PENDING)
    salesperson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class SalesReceipt(Base, TimestampMixin):
    """收款记录"""
    __tablename__ = "sales_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=False)
    receipt_date: Mapped[Date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50))  # cash, transfer, check, scan
    bank_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"))
    reference_no: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class AftersalesRecord(Base, TimestampMixin):
    """售后记录"""
    __tablename__ = "aftersales_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=False)
    record_date: Mapped[Date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(50))  # return, refund, discount, compensation
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ==================== 统一交易流水 ====================

class TransactionRecord(Base, TimestampMixin):
    """统一交易流水（合并日常收支+扫码手续费+付款）"""
    __tablename__ = "transaction_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_date: Mapped[Date] = mapped_column(Date, nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    category: Mapped[TransactionCategory] = mapped_column(Enum(TransactionCategory), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    
    from_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"))
    to_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"))
    
    counterparty_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"))
    counterparty_name: Mapped[Optional[str]] = mapped_column(String(200))
    
    reference_no: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    related_invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("import_invoices.id"))
    related_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("batches.id"))
    
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    confirmed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ==================== 库存层 ====================

class Inventory(Base, TimestampMixin):
    """库存实时查询"""
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    product_spec: Mapped[str] = mapped_column(String(100), nullable=False)
    current_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    reserved_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    available_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    status: Mapped[InventoryStatus] = mapped_column(Enum(InventoryStatus), default=InventoryStatus.IN_STOCK)
    warehouse_location: Mapped[Optional[str]] = mapped_column(String(100))
    last_movement_date: Mapped[Optional[Date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class InventoryMovement(Base, TimestampMixin):
    """库存变动"""
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"), nullable=False)
    movement_date: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reference_type: Mapped[Optional[str]] = mapped_column(String(50))  # sale, processing, adjustment
    reference_id: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ==================== 审计日志 ====================

class AuditTrail(Base, TimestampMixin):
    """审计日志"""
    __tablename__ = "audit_trail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # CREATE, UPDATE, DELETE
    old_values: Mapped[Optional[str]] = mapped_column(Text)
    new_values: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)


class Notification(Base, TimestampMixin):
    """通知中心（小铃铛）"""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    related_type: Mapped[Optional[str]] = mapped_column(String(50))
    related_id: Mapped[Optional[int]] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


# ==================== 系统配置 ====================

class SystemConfig(Base, TimestampMixin):
    """系统配置"""
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    config_type: Mapped[str] = mapped_column(String(20), default="string")  # string, int, float, bool, json
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True)
