import sqlite3

def revert_enums():
    conn = sqlite3.connect('salmon_pms_dev.db')
    cursor = conn.cursor()
    
    # 更新 import_invoices 表中的 customs_status - 改回小写
    status_map = {
        'PENDING_SHIPMENT': 'pending_shipment',
        'IN_TRANSIT': 'in_transit',
        'PENDING_CUSTOMS': 'pending_customs',
        'CUSTOMS_PROCESSING': 'customs_processing',
        'CLEARED': 'cleared',
        'PICKED_UP': 'picked_up'
    }
    for old, new in status_map.items():
        cursor.execute("UPDATE import_invoices SET customs_status = ? WHERE customs_status = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Reverted customs_status {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 import_invoices 表中的 exchange_status
    exchange_map = {
        'NOT_EXCHANGED': 'not_exchanged',
        'PARTIAL': 'partial',
        'COMPLETED': 'completed'
    }
    for old, new in exchange_map.items():
        cursor.execute("UPDATE import_invoices SET exchange_status = ? WHERE exchange_status = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Reverted exchange_status {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 companies 表中的 type
    company_map = {
        'PROCESSING_PLANT': 'processing_plant',
        'FISH_FARM': 'fish_farm',
        'EXPORTER': 'exporter',
        'SUPPLIER': 'supplier',
        'CUSTOMER': 'customer',
        'CUSTOMS_BROKER': 'customs_broker',
        'LOGISTICS': 'logistics',
        'INTERNAL': 'internal'
    }
    for old, new in company_map.items():
        cursor.execute("UPDATE companies SET type = ? WHERE type = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Reverted companies.type {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 products 表中的 category
    product_map = {
        'WHOLE_FISH': 'whole_fish',
        'FINISHED_PRODUCT': 'finished_product',
        'BYPRODUCT': 'byproduct',
        'BOM_MATERIAL': 'bom_material'
    }
    for old, new in product_map.items():
        cursor.execute("UPDATE products SET category = ? WHERE category = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Reverted products.category {old} -> {new}: {cursor.rowcount} rows")
    
    # 更新 batches 表中的 status
    batch_map = {
        'OPEN': 'open',
        'LOCKED': 'locked',
        'SETTLED': 'settled'
    }
    for old, new in batch_map.items():
        cursor.execute("UPDATE batches SET status = ? WHERE status = ?", (new, old))
        if cursor.rowcount > 0:
            print(f"Reverted batches.status {old} -> {new}: {cursor.rowcount} rows")
    
    conn.commit()
    conn.close()
    print("Done!")

if __name__ == '__main__':
    revert_enums()
