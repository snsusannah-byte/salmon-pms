#!/usr/bin/env python3
"""数据库备份脚本"""
import shutil
import os
from datetime import datetime

def backup_db():
    db_path = 'salmon_pms_dev.db'
    backup_dir = 'backups'
    
    if not os.path.exists(db_path):
        print(f"错误: {db_path} 不存在")
        return False
    
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'salmon_pms_dev_{timestamp}.db'
    backup_path = os.path.join(backup_dir, backup_name)
    
    shutil.copy2(db_path, backup_path)
    print(f"备份完成: {backup_path}")
    
    # 保留最近30个备份，删除旧的
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('salmon_pms_dev_') and f.endswith('.db')])
    if len(backups) > 30:
        for old in backups[:-30]:
            os.remove(os.path.join(backup_dir, old))
            print(f"删除旧备份: {old}")
    
    return True

if __name__ == '__main__':
    backup_db()
