-- ============================================
-- 批量补录退货单 SQL
-- 用途：为删除售后调整后残留的数据补录退货单
-- 生成时间: 2026-05-17
-- 注意：TH20260517-001 已存在（XS20260509-006），本次从 002 开始
-- ============================================

BEGIN;

-- 第1条: XS20260503-003 售后¥1,887.60
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-002', 'whole_fish', 385, '2026-05-03', 32, 0, 0, 1887.60, 1887.60, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 1887.60, NOW(), NOW());

-- 第2条: XS20260502-003 售后¥87.40
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-003', 'whole_fish', 375, '2026-05-02', 29, 0, 0, 87.40, 87.40, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 87.40, NOW(), NOW());

-- 第3条: XS20260425-001 售后¥736.42
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-004', 'whole_fish', 360, '2026-04-25', 32, 0, 0, 736.42, 736.42, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 736.42, NOW(), NOW());

-- 第4条: XS20260417-012 售后¥109.20
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-005', 'whole_fish', 183, '2026-04-17', 32, 0, 0, 109.20, 109.20, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 109.20, NOW(), NOW());

-- 第5条: XS20260417-006 售后¥37.80
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-006', 'whole_fish', 177, '2026-04-17', 37, 0, 0, 37.80, 37.80, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 37.80, NOW(), NOW());

-- 第6条: XS20260405-013 售后¥110.50
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-007', 'whole_fish', 211, '2026-04-05', 29, 0, 0, 110.50, 110.50, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 110.50, NOW(), NOW());

-- 第7条: XS20260329-009 售后¥171.00
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-008', 'whole_fish', 220, '2026-03-29', 32, 0, 0, 171.00, 171.00, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 171.00, NOW(), NOW());

-- 第8条: XS20260109-014 售后¥158.10
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-009', 'whole_fish', 314, '2026-01-09', 29, 0, 0, 158.10, 158.10, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 158.10, NOW(), NOW());

-- 第9条: XS20260109-015 售后¥117.60
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-010', 'whole_fish', 315, '2026-01-09', 33, 0, 0, 117.60, 117.60, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 117.60, NOW(), NOW());

-- 第10条: XS20260109-017 售后¥552.00
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-011', 'whole_fish', 317, '2026-01-09', 32, 0, 0, 552.00, 552.00, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 552.00, NOW(), NOW());

-- 第11条: XS20260109-027 售后¥106.68
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-012', 'whole_fish', 327, '2026-01-09', 25, 0, 0, 106.68, 106.68, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 106.68, NOW(), NOW());

-- 第12条: XS20260109-028 售后¥802.50
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-013', 'whole_fish', 328, '2026-01-09', 56, 0, 0, 802.50, 802.50, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 802.50, NOW(), NOW());

-- 第13条: XS20260106-005 售后¥50.00
INSERT INTO return_orders (return_no, sale_type, whole_fish_sale_id, return_date, customer_id, 
    total_weight_kg, total_quantity, total_amount, refund_amount, status, 
    problem_description, internal_notes, created_at, updated_at)
VALUES ('TH20260517-014', 'whole_fish', 334, '2026-01-06', 38, 0, 0, 50.00, 50.00, 'COMPLETED', 
    '历史售后数据补录', '历史数据补录', NOW(), NOW());

INSERT INTO return_items (return_order_id, weight_kg, unit_price, amount, created_at, updated_at)
VALUES (currval('return_orders_id_seq'), 0, 0, 50.00, NOW(), NOW());

COMMIT;

-- ============================================
-- 验证查询
-- ============================================
SELECT '补录完成' as msg, COUNT(*) as count FROM return_orders WHERE return_no LIKE 'TH20260517-%';
