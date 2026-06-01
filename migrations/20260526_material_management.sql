-- ============================================
-- 物料管理模块数据库迁移
-- 2026-05-26
-- ============================================

-- 1. 创建物料分类表
CREATE TABLE IF NOT EXISTS material_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,           -- 分类名称
    code VARCHAR(20) NOT NULL UNIQUE,    -- 分类编码
    sort_order INTEGER DEFAULT 0,          -- 排序
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 在 products 表添加 material_category_id 字段
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'products' AND column_name = 'material_category_id'
    ) THEN
        ALTER TABLE products ADD COLUMN material_category_id INTEGER;
    END IF;
END $$;

-- 添加外键约束（可选，如果 material_categories 表不存在时先不添加）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_products_material_category'
    ) THEN
        ALTER TABLE products
        ADD CONSTRAINT fk_products_material_category
        FOREIGN KEY (material_category_id) REFERENCES material_categories(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- 3. 在 purchase_order_products_v2 表添加 material_id 字段
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'purchase_order_products_v2' AND column_name = 'material_id'
    ) THEN
        ALTER TABLE purchase_order_products_v2 ADD COLUMN material_id INTEGER;
    END IF;
END $$;

-- 添加外键约束
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_popv2_material'
    ) THEN
        ALTER TABLE purchase_order_products_v2
        ADD CONSTRAINT fk_popv2_material
        FOREIGN KEY (material_id) REFERENCES products(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- 4. 初始化物料分类数据
INSERT INTO material_categories (name, code, sort_order, is_active) VALUES
    ('核心包装物料', 'packaging', 1, true),
    ('制冷物料', 'refrigeration', 2, true),
    ('辅助生产办公物料', 'office_aux', 3, true),
    ('食品生产设备', 'production_equip', 4, true)
ON CONFLICT (code) DO NOTHING;

-- 在 products 表添加唯一约束（如果还没有）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'products' AND constraint_name = 'uq_products_code'
    ) THEN
        ALTER TABLE products ADD CONSTRAINT uq_products_code UNIQUE (code);
    END IF;
END $$;

-- 5. 初始化物料数据（基于用户清单）
-- 先获取分类ID
DO $$
DECLARE
    v_packaging_id INTEGER;
    v_refrigeration_id INTEGER;
    v_office_aux_id INTEGER;
    v_production_equip_id INTEGER;
BEGIN
    SELECT id INTO v_packaging_id FROM material_categories WHERE code = 'packaging';
    SELECT id INTO v_refrigeration_id FROM material_categories WHERE code = 'refrigeration';
    SELECT id INTO v_office_aux_id FROM material_categories WHERE code = 'office_aux';
    SELECT id INTO v_production_equip_id FROM material_categories WHERE code = 'production_equip';

    -- 核心包装物料
    INSERT INTO products (category, code, name, spec, unit, material_category_id, is_active, cost_price)
    VALUES
        ('bom_material', 'BM-P-001', '冰袋', '200g', '个', v_packaging_id, true, null),
        ('bom_material', 'BM-P-002', '冰袋', '400g', '个', v_packaging_id, true, null),
        ('bom_material', 'BM-P-003', '泡沫箱+保温袋', '顺丰专用', '套', v_packaging_id, true, null),
        ('bom_material', 'BM-P-004', '金色托', '1600个/件', '件', v_packaging_id, true, null),
        ('bom_material', 'BM-P-005', '吸水垫', '3000个/箱', '箱', v_packaging_id, true, null),
        ('bom_material', 'BM-P-006', '调料包', '3g+10g连体,1000个/箱', '箱', v_packaging_id, true, null),
        ('bom_material', 'BM-P-007', '腰封', 'V01', '张', v_packaging_id, true, null),
        ('bom_material', 'BM-P-008', '腰封', 'V02', '张', v_packaging_id, true, null)
    ON CONFLICT (code) DO UPDATE SET
        material_category_id = EXCLUDED.material_category_id,
        spec = EXCLUDED.spec,
        unit = EXCLUDED.unit,
        updated_at = CURRENT_TIMESTAMP;

    -- 制冷物料 - 干冰
    INSERT INTO products (category, code, name, spec, unit, material_category_id, is_active, cost_price)
    VALUES
        ('bom_material', 'BM-R-001', '干冰', '250g规格', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-002', '干冰', '500g规格', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-003', '干冰', '8斤装', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-004', '干冰', '10斤装', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-005', '干冰', '12斤装', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-006', '干冰', '16斤装', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-007', '干冰', '20斤装', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-008', '干冰', '30斤装', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-009', '干冰', '40斤装', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-010', '干冰', '50斤装', '斤', v_refrigeration_id, true, null),
        ('bom_material', 'BM-R-011', '干冰', '60斤装', '斤', v_refrigeration_id, true, null)
    ON CONFLICT (code) DO UPDATE SET
        material_category_id = EXCLUDED.material_category_id,
        spec = EXCLUDED.spec,
        unit = EXCLUDED.unit,
        updated_at = CURRENT_TIMESTAMP;

    -- 辅助生产办公物料
    INSERT INTO products (category, code, name, spec, unit, material_category_id, is_active, cost_price)
    VALUES
        ('bom_material', 'BM-O-001', '一次性毛巾', null, '条', v_office_aux_id, true, null),
        ('bom_material', 'BM-O-002', '防滑点胶劳保手套', null, '双', v_office_aux_id, true, null),
        ('bom_material', 'BM-O-003', '华夫格餐具清洁抹布', null, '条', v_office_aux_id, true, null),
        ('bom_material', 'BM-O-004', '食品生产车间工作服', null, '套', v_office_aux_id, true, null),
        ('bom_material', 'BM-O-005', '一次性三文鱼外卖打包袋', null, '个', v_office_aux_id, true, null),
        ('bom_material', 'BM-O-006', '加厚一次性丁腈手套', null, '双', v_office_aux_id, true, null),
        ('bom_material', 'BM-O-007', 'A4打印纸', null, '包', v_office_aux_id, true, null),
        ('bom_material', 'BM-O-008', 'A5线圈本', null, '本', v_office_aux_id, true, null),
        ('bom_material', 'BM-O-009', '食品真空包装机', '商用大型款', '台', v_office_aux_id, true, null)
    ON CONFLICT (code) DO UPDATE SET
        material_category_id = EXCLUDED.material_category_id,
        spec = EXCLUDED.spec,
        unit = EXCLUDED.unit,
        updated_at = CURRENT_TIMESTAMP;

    -- 食品生产设备
    INSERT INTO products (category, code, name, spec, unit, material_category_id, is_active, cost_price)
    VALUES
        ('bom_material', 'BM-E-001', '兴长盛真空包装机', '商用大型款', '台', v_production_equip_id, true, null)
    ON CONFLICT (code) DO UPDATE SET
        material_category_id = EXCLUDED.material_category_id,
        spec = EXCLUDED.spec,
        unit = EXCLUDED.unit,
        updated_at = CURRENT_TIMESTAMP;

    -- 更新现有 bom_material 的 material_category_id（如果没设置的话）
    UPDATE products SET material_category_id = v_packaging_id
    WHERE category = 'bom_material' AND material_category_id IS NULL;
END $$;

-- 6. 创建更新触发器（自动更新 updated_at）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_material_categories_updated_at'
    ) THEN
        CREATE TRIGGER trg_material_categories_updated_at
        BEFORE UPDATE ON material_categories
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- 7. 创建物料分类索引
CREATE INDEX IF NOT EXISTS idx_products_material_category_id ON products(material_category_id)
WHERE category = 'bom_material';

CREATE INDEX IF NOT EXISTS idx_popv2_material_id ON purchase_order_products_v2(material_id);
