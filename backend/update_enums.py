import sqlite3

def update_enums():
    conn = sqlite3.connect('salmon_pms_dev.db')
    cursor = conn.cursor()
    
    # 更新 import_invoices 表中的 customs_status - 需要特殊处理
    status_map = {
        'pending_shipment': 'PENDING_SHIPMENT',
        'in_transit': 'IN_TRANSIT',
        'pending_customs': 'PENDING_CUSTOMS',
        'customs_processing': 'CUSTOMS_PROCESSING',
        'cleared': 'CLEARED',
        'picked_up': 'PICKED_UP'
    }
    for old, new in status_map.items():
        cursor.execute("UPDATE import_invoices SET customs_status = ? WHERE customs_status = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Updated customs_status {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 import_invoices 表中的 exchange_status
    exchange_map = {
        'not_exchanged': 'NOT_EXCHANGED',
        'partial': 'PARTIAL',
        'completed': 'COMPLETED'
    }
    for old, new in exchange_map.items():
        cursor.execute("UPDATE import_invoices SET exchange_status = ? WHERE exchange_status = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Updated exchange_status {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 companies 表中的 type
    company_map = {
        'processing_plant': 'PROCESSING_PLANT',
        'fish_farm': 'FISH_FARM',
        'exporter': 'EXPORTER',
        'supplier': 'SUPPLIER',
        'customer': 'CUSTOMER',
        'customs_broker': 'CUSTOMS_BROKER',
        'logistics': 'LOGISTICS',
        'internal': 'INTERNAL'
    }
    for old, new in company_map.items():
        cursor.execute("UPDATE companies SET type = ? WHERE type = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Updated companies.type {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 products 表中的 category
    product_map = {
        'whole_fish': 'WHOLE_FISH',
        'finished_product': 'FINISHED_PRODUCT',
        'byproduct': 'BYPRODUCT',
        'bom_material': 'BOM_MATERIAL'
    }
    for old, new in product_map.items():
        cursor.execute("UPDATE products SET category = ? WHERE category = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Updated products.category {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 batches 表中的 status
    batch_map = {
        'open': 'OPEN',
        'locked': 'LOCKED',
        'settled': 'SETTLED'
    }
    for old, new in batch_map.items():
        cursor.execute("UPDATE batches SET status = ? WHERE status = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Updated batches.status {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 salespersons 表中如果有状态字段的话
    
    conn.commit()
    conn.close()
    print("Done!")

if __name__ == '__main__':
    update_enums()