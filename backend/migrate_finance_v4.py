"""
数据迁移脚本：salmon-finance-v4 → salmon-pms
迁移进口单证、加工厂、渔场、出口商、发票产品明细
"""
import sqlite3
from datetime import datetime, date

# 源数据库
SRC_DB = "/home/sannah/.openclaw/workspace-codeingman/projects/salmon-finance-v4/data/salmon_finance.db"
# 目标数据库
DST_DB = "/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend/salmon_pms_dev.db"

# 主体类型映射
TYPE_MAP = {
    "processing_plant": "processing_plant",
    "fish_farm": "fish_farm",
    "exporter": "exporter",
}

# 报关状态映射
customs_status_map = {
    "未报关": "pending_customs",
    "报关中": "customs_processing",
    "已结关": "cleared",
    "已提货": "picked_up",
    "待发货": "pending_shipment",
    "运输中": "in_transit",
}

# 购汇状态（旧系统没有这个字段，默认未购汇）
exchange_status = "not_exchanged"

def get_or_create_company(dst_conn, name, type_str, code=None):
    """根据名称查找或创建主体，返回 id"""
    cursor = dst_conn.cursor()
    # 尝试精确匹配
    cursor.execute(
        "SELECT id FROM companies WHERE name = ? AND type = ? AND is_active = 1",
        (name, type_str.upper())
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # 尝试模糊匹配
    cursor.execute(
        "SELECT id FROM companies WHERE type = ? AND is_active = 1 AND (name LIKE ? OR ? LIKE '%' || name || '%')",
        (type_str.upper(), f"%{name}%", name)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # 创建新主体
    now = datetime.now().isoformat()
    cursor.execute(
        """INSERT INTO companies (name, type, code, is_active, created_at, updated_at)
           VALUES (?, ?, ?, 1, ?, ?)""",
        (name, type_str.upper(), code or "", now, now)
    )
    dst_conn.commit()
    return cursor.lastrowid

def migrate():
    src = sqlite3.connect(SRC_DB)
    dst = sqlite3.connect(DST_DB)
    
    # 启用外键
    dst.execute("PRAGMA foreign_keys = ON")
    
    print("=== 开始迁移 ===")
    
    # 1. 迁移加工厂
    print("\n--- 迁移加工厂 ---")
    cursor = src.cursor()
    cursor.execute("SELECT id, name, code FROM processing_plants")
    plants = cursor.fetchall()
    plant_id_map = {}  # 旧ID → 新ID
    for old_id, name, code in plants:
        new_id = get_or_create_company(dst, name, "processing_plant", code)
        plant_id_map[old_id] = new_id
        print(f"  加工厂: {name} → ID {new_id}")
    
    # 2. 迁移渔场
    print("\n--- 迁移渔场 ---")
    cursor.execute("SELECT id, name, code FROM fish_farms")
    farms = cursor.fetchall()
    farm_id_map = {}
    for old_id, name, code in farms:
        new_id = get_or_create_company(dst, name, "fish_farm", code)
        farm_id_map[old_id] = new_id
        print(f"  渔场: {name} → ID {new_id}")
    
    # 3. 迁移出口商
    print("\n--- 迁移出口商 ---")
    cursor.execute("SELECT id, name, code FROM exporters")
    exporters = cursor.fetchall()
    exporter_id_map = {}
    for old_id, name, code in exporters:
        new_id = get_or_create_company(dst, name, "exporter", code)
        exporter_id_map[old_id] = new_id
        print(f"  出口商: {name} → ID {new_id}")
    
    # 4. 迁移进口单证
    print("\n--- 迁移进口单证 (27条) ---")
    cursor.execute("""
        SELECT id, invoice_no, invoice_date, kill_date, processing_plant_id,
               fish_farm_id, exporter_id, awb, gross_weight_kg, eta,
               shipping_date, flight_info, origin_info, inspection_info, customs_status
        FROM import_documents
    """)
    invoices = cursor.fetchall()
    invoice_id_map = {}  # 旧ID → 新ID
    
    for row in invoices:
        (old_id, invoice_no, invoice_date, kill_date, pp_id, ff_id, ex_id,
         awb, gross_weight, eta, ship_date, flight, origin, inspection, customs_status) = row
        
        # 映射主体ID
        new_pp_id = plant_id_map.get(pp_id)
        new_ff_id = farm_id_map.get(ff_id)
        new_ex_id = exporter_id_map.get(ex_id)
        
        if not new_pp_id:
            print(f"  ⚠️ 发票 {invoice_no}: 加工厂ID {pp_id} 未找到，跳过")
            continue
        if not new_ff_id:
            print(f"  ⚠️ 发票 {invoice_no}: 渔场ID {ff_id} 未找到，跳过")
            continue
        if not new_ex_id:
            print(f"  ⚠️ 发票 {invoice_no}: 出口商ID {ex_id} 未找到，跳过")
            continue
        
        # 映射状态
        mapped_status = customs_status_map.get(customs_status, "pending_customs")
        
        # 修复eta日期格式（确保月份和日期为2位）
        def fix_datetime(dt_str):
            if not dt_str:
                return None
            # 处理整数类型的日期
            if isinstance(dt_str, int):
                dt_str = str(dt_str)
            try:
                # 尝试解析并重新格式化
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d")
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    return dt_str
        
        # 修复日期格式（处理整数或字符串）
        def fix_date(date_val):
            if not date_val:
                return None
            # 处理整数类型的日期（如 20260119）
            if isinstance(date_val, int):
                date_str = str(date_val)
                if len(date_str) == 8:
                    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                return date_str
            return date_val
        
        eta_fixed = fix_datetime(eta)
        departure_date_fixed = fix_date(ship_date)
        
        now = datetime.now().isoformat()
        
        # 插入 import_invoices
        dst_cursor = dst.cursor()
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
            str(invoice_no),
            invoice_date,
            kill_date,
            None,  # arrival_date 旧系统没有
            new_pp_id,
            new_ff_id,
            new_ex_id,
            0,  # total_amount_usd 旧系统没有
            0,  # total_boxes 旧系统没有
            gross_weight or 0,
            awb,
            gross_weight or 0,
            eta_fixed,
            departure_date_fixed,
            flight,
            origin,
            inspection,
            mapped_status,
            exchange_status,
            False,
            f"从 salmon-finance-v4 迁移: 原状态={customs_status}",
            now,
            now,
        ))
        
        new_invoice_id = dst_cursor.lastrowid
        invoice_id_map[old_id] = new_invoice_id
        print(f"  发票 {invoice_no} → ID {new_invoice_id} (状态: {customs_status}→{mapped_status})")
    
    # 5. 迁移发票产品明细
    print("\n--- 迁移发票产品明细 (52条) ---")
    # 先建立 invoice_no → new_invoice_id 的映射
    invoice_no_map = {}
    dst_cursor = dst.cursor()
    dst_cursor.execute("SELECT id, invoice_no FROM import_invoices")
    for row in dst_cursor.fetchall():
        invoice_no_map[row[1]] = row[0]
    
    cursor.execute("SELECT id, invoice_no, product_spec, box_count, net_weight_kg, unit_price, total_amount FROM invoice_products")
    products = cursor.fetchall()
    
    migrated = 0
    skipped = 0
    for old_id, inv_no, product_spec, box_count, net_weight, unit_price, total_amount in products:
        new_invoice_id = invoice_no_map.get(str(inv_no))
        if not new_invoice_id:
            skipped += 1
            print(f"  ⚠️ 产品明细: 发票号 {inv_no} 未找到，跳过")
            continue
        
        now = datetime.now().isoformat()
        dst.execute("""
            INSERT INTO invoice_products (invoice_id, product_name, product_spec, box_count, net_weight_kg, unit_price, total_amount, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_invoice_id,
            "",  # product_name 旧系统没有，用规格代替
            product_spec or "",
            box_count or 0,
            net_weight or 0,
            unit_price or 0,
            total_amount or 0,
            now,
            now,
        ))
        migrated += 1
    
    print(f"  成功迁移 {migrated} 条，跳过 {skipped} 条")
    
    dst.commit()
    src.close()
    dst.close()
    
    print("\n=== 迁移完成 ===")
    print(f"  加工厂: {len(plants)} 个")
    print(f"  渔场: {len(farms)} 个")
    print(f"  出口商: {len(exporters)} 个")
    print(f"  进口单证: {len(invoice_id_map)} / {len(invoices)} 条")
    print(f"  产品明细: {migrated} / {len(products)} 条")

if __name__ == "__main__":
    migrate()
