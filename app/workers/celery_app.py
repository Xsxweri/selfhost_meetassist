from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery = Celery(
    "meeting_assistant",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                      # 执行完再确认，worker 崩溃可被重投
    worker_prefetch_multiplier=1,             # 长任务(solo池)每次只预取1个，防堆积
    task_soft_time_limit=120,                 # 软超时抛 SoftTimeLimitExceeded，留清理机会
    task_time_limit=180,                      # 硬超时强杀，防僵死占坑
    result_expires=3600,                      # 结果1小时后过期，防 Redis 无限膨胀
    broker_connection_retry_on_startup=True,  # 启动时 broker 短暂不可用自动重连
)


# 周期任务：每天凌晨3点归档90天前的演进链记忆
celery.conf.beat_schedule = {
    "archive-superseded-memories-daily": {
        "task": "archive_superseded_memories",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"before_days": 90},
    },
}