-- 给早期没有购汇单号的记录补充单号
-- 按日期排序，生成 GHYYYYMMDD-NNN 格式

-- 查看需要补充单号的记录
SELECT id, exchange_date, amount_usd, exchange_no 
FROM exchange_records 
WHERE exchange_no IS NULL OR exchange_no = ''
ORDER BY exchange_date, id;

-- 补充单号（按日期分组，生成序号）
WITH numbered AS (
    SELECT 
        id,
        exchange_date,
        ROW_NUMBER() OVER (PARTITION BY exchange_date ORDER BY id) as seq
    FROM exchange_records
    WHERE exchange_no IS NULL OR exchange_no = ''
)
UPDATE exchange_records er
SET exchange_no = 'GH' || REPLACE(n.exchange_date::text, '-', '') || '-' || LPAD(n.seq::text, 3, '0')
FROM numbered n
WHERE er.id = n.id;

-- 验证
SELECT id, exchange_no, exchange_date, amount_usd 
FROM exchange_records 
ORDER BY exchange_date, id;
