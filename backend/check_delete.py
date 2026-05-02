import sqlite3

# 测试删除前查看发票 27 和 28
def check_invoices():
    conn = sqlite3.connect('/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend/salmon_pms_dev.db')
    cursor = conn.cursor()
    
    print("=== 发票 27 和 28 ===")
    cursor.execute('SELECT id, invoice_no, is_locked FROM import_invoices WHERE id IN (27, 28)')
    for row in cursor.fetchall():
        print(row)
    
    print("\n=== 关联的产品明细 ===")
    cursor.execute('SELECT id, invoice_id, product_name FROM invoice_products WHERE invoice_id IN (27, 28)')
    for row in cursor.fetchall():
        print(row)
    
    conn.close()

check_invoices()
