-- 修复：添加唯一约束并初始化物料数据
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'products' AND constraint_name = 'uq_products_code'
    ) THEN
        ALTER TABLE products ADD CONSTRAINT uq_products_code UNIQUE (code);
    END IF;
END $$;

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
    INSERT INTO products (category, code, name, spec, unit, material_category_id, is_active, cost_price, created_at, updated_at)
    VALUES
        ('bom_material', 'BM-P-001', '冰袋', '200g', '个', v_packaging_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-P-002', '冰袋', '400g', '个', v_packaging_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-P-003', '泡沫箱+保温袋', '顺丰专用', '套', v_packaging_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-P-004', '金色托', '1600个/件', '件', v_packaging_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-P-005', '吸水垫', '3000个/箱', '箱', v_packaging_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-P-006', '调料包', '3g+10g连体,1000个/箱', '箱', v_packaging_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-P-007', '腰封', 'V01', '张', v_packaging_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-P-008', '腰封', 'V02', '张', v_packaging_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (code) DO UPDATE SET
        material_category_id = EXCLUDED.material_category_id,
        spec = EXCLUDED.spec,
        unit = EXCLUDED.unit,
        updated_at = CURRENT_TIMESTAMP;

    -- 制冷物料 - 干冰
    INSERT INTO products (category, code, name, spec, unit, material_category_id, is_active, cost_price, created_at, updated_at)
    VALUES
        ('bom_material', 'BM-R-001', '干冰', '250g规格', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-002', '干冰', '500g规格', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-003', '干冰', '8斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-004', '干冰', '10斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-005', '干冰', '12斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-006', '干冰', '16斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-007', '干冰', '20斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-008', '干冰', '30斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-009', '干冰', '40斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-010', '干冰', '50斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-R-011', '干冰', '60斤装', '斤', v_refrigeration_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (code) DO UPDATE SET
        material_category_id = EXCLUDED.material_category_id,
        spec = EXCLUDED.spec,
        unit = EXCLUDED.unit,
        updated_at = CURRENT_TIMESTAMP;

    -- 辅助生产办公物料
    INSERT INTO products (category, code, name, spec, unit, material_category_id, is_active, cost_price, created_at, updated_at)
    VALUES
        ('bom_material', 'BM-O-001', '一次性毛巾', null, '条', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-O-002', '防滑点胶劳保手套', null, '双', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-O-003', '华夫格餐具清洁抹布', null, '条', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-O-004', '食品生产车间工作服', null, '套', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-O-005', '一次性三文鱼外卖打包袋', null, '个', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-O-006', '加厚一次性丁腈手套', null, '双', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-O-007', 'A4打印纸', null, '包', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-O-008', 'A5线圈本', null, '本', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bom_material', 'BM-O-009', '食品真空包装机', '商用大型款', '台', v_office_aux_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (code) DO UPDATE SET
        material_category_id = EXCLUDED.material_category_id,
        spec = EXCLUDED.spec,
        unit = EXCLUDED.unit,
        updated_at = CURRENT_TIMESTAMP;

    -- 食品生产设备
    INSERT INTO products (category, code, name, spec, unit, material_category_id, is_active, cost_price, created_at, updated_at)
    VALUES
        ('bom_material', 'BM-E-001', '兴长盛真空包装机', '商用大型款', '台', v_production_equip_id, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (code) DO UPDATE SET
        material_category_id = EXCLUDED.material_category_id,
        spec = EXCLUDED.spec,
        unit = EXCLUDED.unit,
        updated_at = CURRENT_TIMESTAMP;

    -- 更新现有 bom_material 的 material_category_id（如果没设置的话）
    UPDATE products SET material_category_id = v_packaging_id
    WHERE category = 'bom_material' AND material_category_id IS NULL;
END $$;
