-- 给 import_taxes 表增加 bank_account_id 列（海关税费扣款银行）
ALTER TABLE import_taxes 
ADD COLUMN IF NOT EXISTS bank_account_id INTEGER REFERENCES bank_accounts(id);

-- 给 clearance_costs 表增加 payment_type 列（报关公司付款方式）
ALTER TABLE clearance_costs 
ADD COLUMN IF NOT EXISTS payment_type VARCHAR(20) DEFAULT 'monthly';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_import_taxes_bank_account_id ON import_taxes(bank_account_id);
CREATE INDEX IF NOT EXISTS idx_clearance_costs_payment_type ON clearance_costs(payment_type);
