"""
Celery Tasks Module

This module provides background task processing for the Explicandum system,
including risk monitoring, email notifications, and periodic maintenance tasks.
"""

from .monitoring_tasks import run_risk_detection, cleanup_old_risks
from .celery_app import celery

__all__ = [
    "celery",
    "run_risk_detection",
    "cleanup_old_risks",
]
