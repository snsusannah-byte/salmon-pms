import sqlite3
import re
import shutil

# 先从备份恢复
shutil.copy('backups/salmon_pms_dev_20260501_182238.db', 'salmon_pms_dev.db')
print("Restored from backup")

def fix_dates():
    conn = sqlite3.connect('salmon_pms_dev.db')
    cursor = conn.cursor()
    
    # 查找所有eta字段
    cursor.execute('SELECT id, eta FROM import_invoices WHERE eta IS NOT NULL')
    rows = cursor.fetchall()
    
    fixed = 0
    for id_val, eta in rows:
        if eta:
            # 匹配类似 2026-4-7 01:40 的格式（月份或日期只有1位）
            match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})(.*)', eta)
            if match:
                year, month, day, rest = match.groups()
                # 检查是否需要补零
                if len(month) == 1 or len(day) == 1:
                    month = month.zfill(2)
                    day = day.zfill(2)
                    fixed_eta = f'{year}-{month}-{day}{rest}'
                    cursor.execute('UPDATE import_invoices SET eta = ? WHERE id = ?', (fixed_eta, id_val))
                    fixed += 1
                    print(f'Fixed id={id_val}: {eta} -> {fixed_eta}')
    
    # 修复 departure_date 为整数的问题
    cursor.execute("SELECT id, departure_date FROM import_invoices WHERE departure_date IS NOT NULL")
    rows = cursor.fetchall()
    for id_val, dep_date in rows:
        if isinstance(dep_date, int):
            # 将整数转换为日期字符串
            date_str = str(dep_date)
            if len(date_str) == 8:
                formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                cursor.execute('UPDATE import_invoices SET departure_date = ? WHERE id = ?', (formatted, id_val))
                print(f'Fixed departure_date id={id_val}: {dep_date} -> {formatted}')
    
    conn.commit()
    conn.close()
    print(f'Done! Fixed {fixed} records.')

if __name__ == '__main__':
    fix_dates()