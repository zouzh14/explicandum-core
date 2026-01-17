"""
Monitoring Tasks

This module defines Celery tasks for security monitoring, including
risk detection, email notifications, and system maintenance.
"""

import logging
from celery import current_task
from sqlalchemy.orm import Session
from datetime import datetime

from app.tasks.celery_app import celery
from app.database.base import get_db
from app.core.config import settings
from app.monitoring.risk_detector import RiskDetector
from app.monitoring.alert_manager import alert_manager

logger = logging.getLogger(__name__)


@celery.task(
    name="app.tasks.monitoring_tasks.run_risk_detection",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def run_risk_detection(self):
    """
    Run comprehensive risk detection scan

    This task:
    1. Detects all types of security risks
    2. Stores new risk events in database
    3. Sends email notifications for critical/high risks
    4. Updates monitoring statistics

    Returns:
        dict: Scan results summary
    """
    if not settings.RISK_MONITORING_ENABLED:
        logger.info("Risk monitoring is disabled, skipping scan")
        return {"status": "skipped", "reason": "monitoring_disabled"}

    task_id = self.request.id
    start_time = datetime.utcnow()

    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting risk detection scan", "progress": 0},
        )

        # Get database session
        db = next(get_db())

        # Initialize risk detector
        detector = RiskDetector()

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Running risk detection algorithms", "progress": 25},
        )

        # Run risk detection
        risks = detector.detect_all_risks(db)

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Processing detected risks", "progress": 50},
        )

        # Process new risks (store in database and send emails)
        # Note: In Celery tasks, we need to handle async calls properly
        import asyncio

        process_results = asyncio.run(alert_manager.process_new_risks(risks, db))

        # Update task state
        self.update_state(
            state="PROGRESS", meta={"status": "Finalizing scan results", "progress": 75}
        )

        # Count risks by level
        risk_counts = {
            "critical": len([r for r in risks if r.level.value == "critical"]),
            "high": len([r for r in risks if r.level.value == "high"]),
            "medium": len([r for r in risks if r.level.value == "medium"]),
            "low": len([r for r in risks if r.level.value == "low"]),
        }

        # Calculate scan duration
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        # Prepare result
        result = {
            "status": "completed",
            "task_id": task_id,
            "scan_timestamp": start_time.isoformat(),
            "duration_seconds": duration_seconds,
            "total_risks_detected": len(risks),
            "new_risks_stored": process_results.get("stored", 0),
            "emails_sent": process_results.get("emails_sent", 0),
            "risk_counts": risk_counts,
            "errors": process_results.get("errors", []),
            "monitoring_enabled": settings.RISK_MONITORING_ENABLED,
        }

        # Log completion
        logger.info(
            f"Risk detection scan completed: {len(risks)} risks detected, "
            f"{process_results.get('stored', 0)} new risks stored, "
            f"{process_results.get('emails_sent', 0)} emails sent"
        )

        # Update task state to completed
        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Risk detection completed successfully",
                "progress": 100,
                **result,
            },
        )

        return result

    except Exception as e:
        error_msg = f"Risk detection scan failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Update task state to failure
        self.update_state(
            state="FAILURE", meta={"status": error_msg, "error": str(e), "progress": 0}
        )

        # Re-raise exception to trigger retry
        raise

    finally:
        # Ensure database session is closed
        if "db" in locals():
            db.close()


# Daily report task disabled - not sending daily security summary reports
#
# @celery.task(
#     name="app.tasks.monitoring_tasks.send_daily_report",
#     bind=True,
#     autoretry_for=(Exception,),
#     retry_backoff=True,
#     retry_kwargs={"max_retries": 3, "countdown": 300},
# )
# def send_daily_report(self):
#     """
#     Send daily security report via email
#
#     This task:
#     1. Collects risk events from last 24 hours
#     2. Generates daily security summary
#     3. Sends email report to administrators
#
#     Returns:
#         dict: Report sending results
#     """
#     if not settings.RISK_MONITORING_ENABLED:
#         logger.info("Risk monitoring is disabled, skipping daily report")
#         return {"status": "skipped", "reason": "monitoring_disabled"}
#
#     task_id = self.request.id
#     start_time = datetime.utcnow()
#
#     try:
#         # Update task state
#         self.update_state(
#             state="PROGRESS",
#             meta={"status": "Starting daily report generation", "progress": 0},
#         )
#
#         # Get database session
#         db = next(get_db())
#
#         # Update task state
#         self.update_state(
#             state="PROGRESS",
#             meta={"status": "Collecting risk data from last 24 hours", "progress": 25},
#         )
#
#         # Send daily report
#         import asyncio
#
#         success = asyncio.run(alert_manager.send_daily_report(db))
#
#         # Update task state
#         self.update_state(
#             state="PROGRESS", meta={"status": "Finalizing daily report", "progress": 75}
#         )
#
#         # Calculate duration
#         end_time = datetime.utcnow()
#         duration_seconds = (end_time - start_time).total_seconds()
#
#         # Prepare result
#         result = {
#             "status": "completed" if success else "failed",
#             "task_id": task_id,
#             "report_timestamp": start_time.isoformat(),
#             "duration_seconds": duration_seconds,
#             "email_sent": success,
#             "recipients": [settings.ALERT_EMAIL, settings.CC_EMAIL]
#             if settings.CC_EMAIL
#             else [settings.ALERT_EMAIL],
#             "monitoring_enabled": settings.RISK_MONITORING_ENABLED,
#         }
#
#         # Log completion
#         if success:
#             logger.info(
#                 f"Daily security report sent successfully to {settings.ALERT_EMAIL}"
#             )
#         else:
#             logger.error("Failed to send daily security report")
#
#         # Update task state
#         state = "SUCCESS" if success else "FAILURE"
#         self.update_state(
#             state=state,
#             meta={
#                 "status": f"Daily report {'sent' if success else 'failed'}",
#                 "progress": 100,
#                 **result,
#             },
#         )
#
#         return result
#
#     except Exception as e:
#         error_msg = f"Daily report generation failed: {str(e)}"
#         logger.error(error_msg, exc_info=True)
#
#         # Update task state to failure
#         self.update_state(
#             state="FAILURE", meta={"status": error_msg, "error": str(e), "progress": 0}
#         )
#
#         # Re-raise exception to trigger retry
#         raise
#
#     finally:
#         # Ensure database session is closed
#         if "db" in locals():
#             db.close()


@celery.task(
    name="app.tasks.monitoring_tasks.cleanup_old_risks",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2, "countdown": 600},
)
def cleanup_old_risks(self, days_to_keep: int = 30):
    """
    Clean up old resolved risk events

    This task:
    1. Identifies resolved risk events older than specified days
    2. Removes them from database
    3. Logs cleanup statistics

    Args:
        days_to_keep: Number of days to keep resolved risks (default: 30)

    Returns:
        dict: Cleanup results
    """
    task_id = self.request.id
    start_time = datetime.utcnow()

    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting risk cleanup process", "progress": 0},
        )

        # Get database session
        db = next(get_db())

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Identifying old resolved risks", "progress": 25},
        )

        # Perform cleanup
        deleted_count = alert_manager.cleanup_old_risks(db, days_to_keep)

        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Finalizing cleanup process", "progress": 75},
        )

        # Calculate duration
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        # Prepare result
        result = {
            "status": "completed",
            "task_id": task_id,
            "cleanup_timestamp": start_time.isoformat(),
            "duration_seconds": duration_seconds,
            "days_kept": days_to_keep,
            "deleted_count": deleted_count,
            "monitoring_enabled": settings.RISK_MONITORING_ENABLED,
        }

        # Log completion
        logger.info(f"Risk cleanup completed: {deleted_count} old risks deleted")

        # Update task state to completed
        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Risk cleanup completed successfully",
                "progress": 100,
                **result,
            },
        )

        return result

    except Exception as e:
        error_msg = f"Risk cleanup failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Update task state to failure
        self.update_state(
            state="FAILURE", meta={"status": error_msg, "error": str(e), "progress": 0}
        )

        # Re-raise exception to trigger retry
        raise

    finally:
        # Ensure database session is closed
        if "db" in locals():
            db.close()


@celery.task(
    name="app.tasks.monitoring_tasks.get_monitoring_status",
    bind=True,
)
def get_monitoring_status(self):
    """
    Get current monitoring system status

    Returns:
        dict: Current monitoring status and statistics
    """
    try:
        # Get database session
        db = next(get_db())

        # Get risk statistics
        stats = alert_manager.get_risk_statistics(db, 24)

        # Get email service status
        email_status = alert_manager.get_email_service_status()

        # Get task information
        inspect = celery.control.inspect()
        active_tasks = inspect.active()

        # Prepare result
        result = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_enabled": settings.RISK_MONITORING_ENABLED,
            "risk_statistics": stats,
            "email_service": email_status,
            "active_tasks": active_tasks,
            "configuration": {
                "risk_detection_interval": settings.RISK_DETECTION_INTERVAL,
                "daily_report_time": settings.DAILY_REPORT_TIME,
                "alert_email": settings.ALERT_EMAIL,
                "cc_email": settings.CC_EMAIL,
            },
        }

        return result

    except Exception as e:
        error_msg = f"Failed to get monitoring status: {str(e)}"
        logger.error(error_msg, exc_info=True)

        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "monitoring_enabled": settings.RISK_MONITORING_ENABLED,
        }

    finally:
        # Ensure database session is closed
        if "db" in locals():
            db.close()


@celery.task(
    name="app.tasks.monitoring_tasks.test_email_configuration",
    bind=True,
)
def test_email_configuration(self):
    """
    Test email service configuration

    Returns:
        dict: Email configuration test results
    """
    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Testing email configuration", "progress": 50},
        )

        # Send test email
        import asyncio

        success = asyncio.run(alert_manager.email_service.send_test_email())

        # Prepare result
        result = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "email_sent": success,
            "email_service_status": alert_manager.get_email_service_status(),
            "recipients": [settings.ALERT_EMAIL, settings.CC_EMAIL]
            if settings.CC_EMAIL
            else [settings.ALERT_EMAIL],
        }

        # Update task state
        state = "SUCCESS" if success else "FAILURE"
        self.update_state(
            state=state,
            meta={
                "status": f"Email test {'passed' if success else 'failed'}",
                "progress": 100,
                **result,
            },
        )

        return result

    except Exception as e:
        error_msg = f"Email configuration test failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Update task state to failure
        self.update_state(
            state="FAILURE", meta={"status": error_msg, "error": str(e), "progress": 0}
        )

        return {
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "email_sent": False,
        }
