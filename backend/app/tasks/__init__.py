"""
Celery 任务模块

使用方式:
    # 启动 worker (开发环境)
    celery -A app.tasks worker --loglevel=info -Q reports,exports

    # 启动 worker (生产环境，4进程)
    celery -A app.tasks worker --loglevel=info --concurrency=4 -Q reports,exports

    # 监控
    celery -A app.tasks flower --port=5555
"""
from app.tasks.celery_app import celery_app

# 导出常用任务（方便直接调用）
from app.tasks.report_tasks import generate_batch_report_task, generate_payable_statement_task
from app.tasks.export_tasks import export_sales_to_csv_task, export_finance_transactions_task

__all__ = [
    "celery_app",
    "generate_batch_report_task",
    "generate_payable_statement_task",
    "export_sales_to_csv_task",
    "export_finance_transactions_task",
]
