-- 给 exchange_records 表增加 importer_id 列
ALTER TABLE exchange_records 
ADD COLUMN IF NOT EXISTS importer_id INTEGER REFERENCES companies(id);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_exchange_records_importer_id ON exchange_records(importer_id);

-- 找到"浙江中挪进出口有限公司"的公司ID
DO $$
DECLARE
    zj_importer_id INTEGER;
BEGIN
    -- 查找浙江中挪进出口有限公司
    SELECT id INTO zj_importer_id FROM companies WHERE name = '浙江中挪进出口有限公司' LIMIT 1;
    
    IF zj_importer_id IS NULL THEN
        RAISE NOTICE '未找到浙江中挪进出口有限公司，跳过数据更新';
    ELSE
        -- 更新现有 exchange_records 的 importer_id
        UPDATE exchange_records SET importer_id = zj_importer_id WHERE importer_id IS NULL;
        RAISE NOTICE '已更新 exchange_records.importer_id = %', zj_importer_id;
    END IF;
END $$;
