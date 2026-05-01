"""
安全修改 fish_farm_id 为 nullable 并补导入 8468
"""
import sqlite3
from datetime import datetime

DB_PATH = "salmon_pms_dev.db"

def safe_migrate():
    src = sqlite3.connect("/home/sannah/.openclaw/workspace-codeingman/projects/salmon-finance-v4/data/salmon_finance.db")
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(DB_PATH)
    dst.row_factory = sqlite3.Row

    print("--- Step 1: 创建新表（fish_farm_id nullable）---")
    c = dst.cursor()
    c.execute("PRAGMA table_info(import_invoices)")
    old_cols = c.fetchall()
    print(f"旧表列: {[col[1] for col in old_cols]}")

    c.execute("SELECT COUNT(*) FROM import_invoices")
    old_count = c.fetchone()[0]
    print(f"旧表数据: {old_count} 条")

    create_sql = """
    CREATE TABLE import_invoices_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no VARCHAR(50) NOT NULL,
        invoice_date DATE NOT NULL,
        kill_date DATE,
        arrival_date DATE,
        processing_plant_id INTEGER NOT NULL,
        fish_farm_id INTEGER,
        exporter_id INTEGER NOT NULL,
        total_amount_usd NUMERIC(15, 2) NOT NULL DEFAULT 0,
        total_boxes INTEGER NOT NULL DEFAULT 0,
        total_weight_kg NUMERIC(12, 3) NOT NULL DEFAULT 0,
        awb_no VARCHAR(50),
        gross_weight_kg NUMERIC(12, 3),
        eta DATETIME,
        departure_date DATE,
        flight_info VARCHAR(100),
        origin_certificate VARCHAR(100),
        inspection_certificate VARCHAR(100),
        customs_status VARCHAR(18) NOT NULL DEFAULT 'pending_customs',
        exchange_status VARCHAR(13) NOT NULL DEFAULT 'not_exchanged',
        is_locked BOOLEAN NOT NULL DEFAULT 0,
        notes TEXT,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        unit_price_usd NUMERIC(12, 4),
        estimated_exchange_rate NUMERIC(10, 6),
        estimated_cost_cny NUMERIC(15, 2),
        actual_cost_cny NUMERIC(15, 2)
    )
    """
    dst.execute(create_sql)

    print("--- Step 2: 复制数据 ---")
    c.execute("SELECT * FROM import_invoices")
    rows = c.fetchall()
    for row in rows:
        vals = tuple(row)
        placeholders = ",".join(["?"] * len(vals))
        dst.execute(f"INSERT INTO import_invoices_new VALUES ({placeholders})", vals)

    c.execute("SELECT COUNT(*) FROM import_invoices_new")
    new_count = c.fetchone()[0]
    print(f"新表数据: {new_count} 条")

    if new_count != old_count:
        raise RuntimeError(f"数据复制失败: 旧{old_count} ≠ 新{new_count}")

    # 验证几条数据
    c.execute("SELECT id, invoice_no FROM import_invoices_new ORDER BY id LIMIT 3")
    print("前3条:", c.fetchall())
    c.execute("SELECT MAX(id) FROM import_invoices_new")
    max_id = c.fetchone()[0]
    print(f"最大 ID: {max_id}")

    print("--- Step 3: 替换表 ---")
    dst.execute("DROP TABLE import_invoices")
    dst.execute("ALTER TABLE import_invoices_new RENAME TO import_invoices")

    # 修复 sqlite_sequence
    dst.execute("DELETE FROM sqlite_sequence WHERE name = 'import_invoices'")
    dst.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('import_invoices', ?)", (max_id,))

    dst.commit()
    print("✅ 表结构已修改，fish_farm_id 现为 nullable")

    # Step 4: 导入 8468
    print("\n--- Step 4: 补导入发票 8468 ---")
    cursor = src.cursor()
    cursor.execute("""
        SELECT id, invoice_no, invoice_date, kill_date, processing_plant_id,
               fish_farm_id, exporter_id, awb, gross_weight_kg, eta,
               shipping_date, flight_info, origin_info, inspection_info, customs_status
        FROM import_documents WHERE invoice_no = '8468'
    """)
    row = cursor.fetchone()
    if not row:
        print("❌ 旧数据库中未找到 8468")
        return

    print(f"找到旧数据: {dict(row)}")

    dst_cursor = dst.cursor()
    dst_cursor.execute("SELECT id, name FROM companies WHERE type = 'PROCESSING_PLANT'")
    plants = {r['name'].upper(): r['id'] for r in dst_cursor.fetchall()}

    dst_cursor.execute("SELECT id, name FROM companies WHERE type = 'FISH_FARM'")
    farms = {r['name'].upper(): r['id'] for r in dst_cursor.fetchall()}

    dst_cursor.execute("SELECT id, name FROM companies WHERE type = 'EXPORTER'")
    exporters = {r['name'].upper(): r['id'] for r in dst_cursor.fetchall()}

    cursor.execute("SELECT id, name FROM processing_plants WHERE id = ?", (row['processing_plant_id'],))
    plant_row = cursor.fetchone()
    plant_name = plant_row['name'].upper() if plant_row else None

    cursor.execute("SELECT id, name FROM fish_farms WHERE id = ?", (row['fish_farm_id'],))
    farm_row = cursor.fetchone()
    farm_name = farm_row['name'].upper() if farm_row else None

    cursor.execute("SELECT id, name FROM exporters WHERE id = ?", (row['exporter_id'],))
    exporter_row = cursor.fetchone()
    exporter_name = exporter_row['name'].upper() if exporter_row else None

    new_pp_id = plants.get(plant_name)
    if not new_pp_id and plant_name and 'ARN' in plant_name and 'LAKS' in plant_name:
        for name, cid in plants.items():
            if 'ARN' in name and 'LAKS' in name:
                new_pp_id = cid
                break

    new_ff_id = farms.get(farm_name) if farm_name else None
    new_ex_id = exporters.get(exporter_name)

    print(f"映射结果: 加工厂={plant_name}→{new_pp_id}, 渔场={farm_name}→{new_ff_id}, 出口商={exporter_name}→{new_ex_id}")

    customs_status_map = {
        "已结关": "cleared",
        "未报关": "pending_customs",
        "报关中": "in_customs",
        "清关中": "customs_cleared",
    }
    mapped_status = customs_status_map.get(row['customs_status'], "pending_customs")

    now = datetime.now().isoformat()

    dst_cursor.execute("""
        INSERT INTO import_invoices (
            invoice_no, invoice_date, kill_date, arrival_date,
            processing_plant_id, fish_farm_id, exporter_id,
            total_amount_usd, total_boxes, total_weight_kg,
            awb_no, gross_weight_kg, eta, departure_date,
            flight_info, origin_certificate, inspection_certificate,
            customs_status, exchange_status, is_locked,
            notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(row['invoice_no']),
        row['invoice_date'],
        row['kill_date'],
        None,
        new_pp_id,
        new_ff_id,
        new_ex_id,
        0,
        0,
        row['gross_weight_kg'] or 0,
        row['awb'],
        row['gross_weight_kg'] or 0,
        row['eta'],
        row['shipping_date'],
        row['flight_info'],
        row['origin_info'],
        row['inspection_info'],
        mapped_status,
        "pending",
        False,
        f"从 salmon-finance-v4 迁移（补）: 原状态={row['customs_status']}",
        now,
        now,
    ))

    new_invoice_id = dst_cursor.lastrowid
    print(f"✅ 发票 8468 已导入，新 ID: {new_invoice_id}")

    cursor.execute("""
        SELECT product_spec, box_count, net_weight_kg, unit_price, total_amount
        FROM invoice_products WHERE invoice_no = '8468'
    """)
    products = cursor.fetchall()
    for p in products:
        dst_cursor.execute("""
            INSERT INTO invoice_products (invoice_id, product_name, product_spec, box_count, net_weight_kg, unit_price, total_amount, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_invoice_id,
            "",
            p['product_spec'] or "",
            p['box_count'] or 0,
            p['net_weight_kg'] or 0,
            p['unit_price'] or 0,
            p['total_amount'] or 0,
            now,
            now,
        ))
    print(f"✅ 产品明细 {len(products)} 条已导入")

    dst.commit()

    # Verify
    dst_cursor.execute("SELECT id, invoice_no FROM import_invoices ORDER BY id")
    all_rows = dst_cursor.fetchall()
    print(f"\n验证: 共 {len(all_rows)} 条发票")
    print("最后几条:", all_rows[-3:])

    src.close()
    dst.close()
    print("🎉 全部完成")


if __name__ == "__main__":
    safe_migrate()
