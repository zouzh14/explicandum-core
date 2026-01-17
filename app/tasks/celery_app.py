"""
Celery Application Configuration

This module configures the Celery application for background task processing.
"""

from celery import Celery
from app.core.config import settings

# Create Celery instance
celery = Celery(
    "explicandum",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BROKER_URL,
    include=[
        "app.tasks.monitoring_tasks",
    ],
)

# Configure Celery
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configure beat schedule for periodic tasks
celery.conf.beat_schedule = {
    # Risk monitoring - run every 5 minutes
    "risk-monitoring": {
        "task": "app.tasks.monitoring_tasks.run_risk_detection",
        "schedule": settings.RISK_DETECTION_INTERVAL,  # 300 seconds (5 minutes)
        "options": {"queue": "monitoring"},
    },
    # Daily security report - DISABLED - not sending daily security summary reports
    # "daily-security-report": {
    #     "task": "app.tasks.monitoring_tasks.send_daily_report",
    #     "schedule": settings.DAILY_REPORT_TIME,  # 09:00 UTC
    #     "options": {"queue": "monitoring"},
    # },
    # Cleanup old risks - run once a week
    "cleanup-old-risks": {
        "task": "app.tasks.monitoring_tasks.cleanup_old_risks",
        "schedule": 7 * 24 * 60 * 60,  # 7 days in seconds
        "options": {"queue": "maintenance"},
    },
}

# Configure queues
celery.conf.task_routes = {
    "app.tasks.monitoring_tasks.run_risk_detection": {"queue": "monitoring"},
    # "app.tasks.monitoring_tasks.send_daily_report": {"queue": "monitoring"},  # DISABLED
    "app.tasks.monitoring_tasks.cleanup_old_risks": {"queue": "maintenance"},
}

# Configure worker settings
celery.conf.worker_direct = True
celery.conf.worker_send_task_events = True
celery.conf.task_send_sent_event = True

# Error handling
celery.conf.task_reject_on_worker_lost = True
celery.conf.task_acks_late = True
celery.conf.worker_disable_rate_limits = False

# Monitoring settings
celery.conf.worker_log_color = True
celery.conf.worker_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
)
celery.conf.worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"

# Result backend settings
celery.conf.result_expires = 60 * 60 * 24  # 24 hours
celery.conf.result_backend_transport_options = {
    "master_name": "mymaster",
    "visibility_timeout": 3600,
}

# Security settings
celery.conf.worker_send_task_events = True
celery.conf.task_send_sent_event = True
celery.conf.task_publish_retry = True
celery.conf.task_publish_retry_policy = {
    "max_retries": 3,
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 0.2,
}

# Performance optimization
celery.conf.broker_pool_limit = 10
celery.conf.broker_connection_retry_on_startup = True
celery.conf.broker_connection_retry = True
celery.conf.broker_connection_max_retries = 10


# Health check task
@celery.task(name="app.tasks.health_check")
def health_check():
    """Simple health check task for monitoring"""
    return {"status": "healthy", "timestamp": "now"}


# Task monitoring
@celery.task(name="app.tasks.get_active_tasks")
def get_active_tasks():
    """Get information about active tasks"""
    inspect = celery.control.inspect()
    active = inspect.active()
    scheduled = inspect.scheduled()
    reserved = inspect.reserved()

    return {
        "active_tasks": active,
        "scheduled_tasks": scheduled,
        "reserved_tasks": reserved,
    }


# Task cleanup
@celery.task(name="app.tasks.purge_queue")
def purge_queue(queue_name: str):
    """Purge all tasks from a specific queue"""
    with celery.connection() as conn:
        return conn.default_channel.queue_purge(queue_name)


# Task statistics
@celery.task(name="app.tasks.get_task_stats")
def get_task_stats():
    """Get task execution statistics"""
    inspect = celery.control.inspect()
    stats = inspect.stats()

    return {
        "worker_stats": stats,
        "registered_tasks": list(celery.tasks.keys()),
        "active_queues": list(celery.conf.task_routes.keys()),
    }


if __name__ == "__main__":
    celery.start()
