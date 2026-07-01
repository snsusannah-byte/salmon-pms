"""
Celery 异步任务配置

使用方式:
    # 启动 worker
    celery -A app.tasks worker --loglevel=info

    # 调用任务
    from app.tasks import generate_report_task
    generate_report_task.delay(report_type="batch", batch_id=123)
"""
from celery import Celery
from app.core.config import settings

# 创建 Celery 实例
celery_app = Celery(
    "salmon_pms",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.report_tasks",
        "app.tasks.export_tasks",
    ],
)

# 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,  # 公平调度
    result_expires=3600,  # 结果1小时后过期
)

# 路由配置：报表生成走专用队列
celery_app.conf.task_routes = {
    "app.tasks.report_tasks.*": {"queue": "reports"},
    "app.tasks.export_tasks.*": {"queue": "exports"},
}

# 启动信号
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """配置定时任务"""
    # 每天凌晨3点备份提醒（可扩展为自动备份）
    # sender.add_periodic_task(
    #     crontab(hour=3, minute=0),
    #     backup_database_task.s(),
    # )
    pass
