"""
Monitoring API Endpoints

This module provides REST API endpoints for the security monitoring system,
including risk detection, alert management, and system status.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.database.base import get_db
from app.database.models import User
from app.monitoring.risk_detector import RiskDetector, RiskLevel, RiskType
from app.monitoring.alert_manager import alert_manager
from app.services.email_service import email_service
from fastapi.security import OAuth2PasswordBearer
from app.core.auth import decode_access_token
from fastapi import HTTPException, status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_admin_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """获取当前管理员用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


# Pydantic models for API requests/responses
class RiskEventResponse(BaseModel):
    id: str
    type: str
    level: str
    title: str
    description: str
    value: float
    threshold: float
    timestamp: str
    resolved: bool
    actions: List[str]
    metadata: Dict[str, Any]


class RiskStatisticsResponse(BaseModel):
    period_hours: int
    total_risks: int
    unresolved_risks: int
    resolved_risks: int
    risks_by_level: Dict[str, int]
    risks_by_type: Dict[str, int]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class EmailStatusResponse(BaseModel):
    configured: bool
    api_key_configured: bool
    from_email: str
    alert_email: str
    cc_email: str
    service_provider: str


class ResolveRiskRequest(BaseModel):
    resolved_by: Optional[str] = "admin"


class TestEmailRequest(BaseModel):
    test_type: Optional[str] = "basic"  # basic, critical_alert, daily_report


@router.get("/risks", response_model=List[RiskEventResponse])
async def get_current_risks(
    unresolved_only: bool = True,
    limit: int = 50,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Get current risk events

    Args:
        unresolved_only: Only return unresolved risks
        limit: Maximum number of risks to return
        level: Filter by risk level (critical, high, medium, low)
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        List of risk events
    """
    try:
        if level:
            try:
                risk_level = RiskLevel(level)
                risks = alert_manager.get_risks_by_level(
                    db, risk_level, unresolved_only
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid risk level: {level}"
                )
        else:
            risks = alert_manager.get_unresolved_risks(db, limit)

        # Convert to response format
        risk_responses = []
        for risk in risks:
            import json

            actions = json.loads(risk.actions) if risk.actions else []
            metadata = json.loads(risk.metadata) if risk.metadata else {}

            risk_response = RiskEventResponse(
                id=risk.id,
                type=risk.type,
                level=risk.level,
                title=risk.title,
                description=risk.description,
                value=risk.value,
                threshold=risk.threshold,
                timestamp=risk.timestamp.isoformat(),
                resolved=risk.resolved,
                actions=actions,
                metadata=metadata,
            )
            risk_responses.append(risk_response)

        return risk_responses

    except Exception as e:
        logger.error(f"Error getting current risks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve risk events")


@router.get("/risks/statistics", response_model=RiskStatisticsResponse)
async def get_risk_statistics(
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Get risk statistics for the specified time period

    Args:
        hours: Number of hours to look back (default: 24)
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        Risk statistics summary
    """
    try:
        stats = alert_manager.get_risk_statistics(db, hours)
        return RiskStatisticsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting risk statistics: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve risk statistics"
        )


@router.post("/risks/scan")
async def trigger_risk_scan(
    background_tasks: BackgroundTasks,
    auto_email: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Trigger manual risk detection scan

    Args:
        background_tasks: FastAPI background tasks
        auto_email: Whether to send email notifications for critical risks
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        Scan results summary
    """
    try:
        # Run risk detection
        detector = RiskDetector()
        risks = detector.detect_all_risks(db)

        # Process new risks in background
        if auto_email:
            background_tasks.add_task(alert_manager.process_new_risks, risks, db)
        else:
            background_tasks.add_task(alert_manager.store_risk_events, risks, db)

        # Return immediate results
        critical_count = len([r for r in risks if r.level == RiskLevel.CRITICAL])
        high_count = len([r for r in risks if r.level == RiskLevel.HIGH])

        return {
            "message": "Risk scan completed successfully",
            "total_risks_detected": len(risks),
            "critical_risks": critical_count,
            "high_risks": high_count,
            "medium_risks": len([r for r in risks if r.level == RiskLevel.MEDIUM]),
            "low_risks": len([r for r in risks if r.level == RiskLevel.LOW]),
            "auto_email_sent": auto_email and (critical_count > 0 or high_count > 0),
            "scan_timestamp": detector.risk_thresholds,  # Include some context
        }

    except Exception as e:
        logger.error(f"Error during risk scan: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to perform risk scan")


@router.post("/risks/{risk_id}/resolve")
async def resolve_risk(
    risk_id: str,
    request: ResolveRiskRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Mark a risk event as resolved

    Args:
        risk_id: ID of the risk to resolve
        request: Resolution request data
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        Resolution result
    """
    try:
        resolved_by = request.resolved_by or current_user.get("email", "admin")
        success = alert_manager.resolve_risk(risk_id, resolved_by, db)

        if success:
            return {
                "message": f"Risk {risk_id} marked as resolved",
                "resolved_by": resolved_by,
                "risk_id": risk_id,
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"Risk event {risk_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving risk {risk_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to resolve risk event")


@router.get("/email/status", response_model=EmailStatusResponse)
async def get_email_status(current_user: dict = Depends(get_current_admin_user)):
    """
    Get email service configuration status

    Args:
        current_user: Current authenticated admin user

    Returns:
        Email service status
    """
    try:
        status = alert_manager.get_email_service_status()
        return EmailStatusResponse(**status)

    except Exception as e:
        logger.error(f"Error getting email status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve email status")


@router.post("/email/test")
async def send_test_email(
    request: TestEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Send a test email to verify email configuration

    Args:
        request: Test email request data
        background_tasks: FastAPI background tasks
        current_user: Current authenticated admin user

    Returns:
        Test email result
    """
    try:
        if request.test_type == "basic":
            success = await email_service.send_test_email()
            message = "Basic test email sent successfully"
        elif request.test_type == "critical_alert":
            # Create a fake critical risk for testing
            from app.monitoring.risk_detector import RiskEvent, RiskType
            from datetime import datetime

            test_risk = RiskEvent(
                id=f"test_critical_{datetime.now().timestamp()}",
                type=RiskType.SECURITY,
                level=RiskLevel.CRITICAL,
                title="Test Critical Security Alert",
                description="This is a test critical alert to verify email notifications are working correctly.",
                value=1,
                threshold=0,
                timestamp=datetime.now(),
                actions=["Verify email configuration", "Check email delivery"],
                metadata={"test": True, "triggered_by": current_user.get("email")},
            )

            success = await email_service.send_critical_alert([test_risk])
            message = "Critical alert test email sent successfully"
        elif request.test_type == "daily_report":
            # Send daily report test
            success = await email_service.send_daily_report([])
            message = "Daily report test email sent successfully"
        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid test type: {request.test_type}"
            )

        if success:
            return {
                "message": message,
                "test_type": request.test_type,
                "sent_to": email_service.alert_email,
                "cc_to": email_service.cc_email,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send test email")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send test email")


@router.post("/email/daily-report")
async def send_daily_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Send daily security report manually

    Args:
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        Daily report result
    """
    try:
        # Send daily report in background
        background_tasks.add_task(alert_manager.send_daily_report, db)

        return {
            "message": "Daily report is being generated and sent",
            "triggered_by": current_user.get("email"),
            "report_time": "last 24 hours",
        }

    except Exception as e:
        logger.error(f"Error sending daily report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send daily report")


@router.get("/system/health")
async def get_system_health(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_admin_user)
):
    """
    Get monitoring system health status

    Args:
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        System health information
    """
    try:
        # Get basic statistics
        stats = alert_manager.get_risk_statistics(db, 24)
        email_status = alert_manager.get_email_service_status()

        # Check system components
        health_status = {
            "monitoring_enabled": True,
            "risk_detection": "operational",
            "email_service": "operational"
            if email_status["configured"]
            else "misconfigured",
            "database": "operational",
            "last_scan": "manual_scan_required",
            "active_risks": stats["unresolved_risks"],
            "critical_risks": stats["critical_count"],
            "high_risks": stats["high_count"],
            "email_configured": email_status["configured"],
            "system_uptime": "operational",
        }

        # Overall health status
        if stats["critical_count"] > 0:
            overall_health = "critical"
        elif stats["high_count"] > 5:
            overall_health = "warning"
        elif not email_status["configured"]:
            overall_health = "warning"
        else:
            overall_health = "healthy"

        health_status["overall_health"] = overall_health

        return health_status

    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")


@router.delete("/risks/cleanup")
async def cleanup_old_risks(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Clean up old resolved risk events

    Args:
        days: Number of days to keep resolved risks (default: 30)
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        Cleanup result
    """
    try:
        deleted_count = alert_manager.cleanup_old_risks(db, days)

        return {
            "message": f"Cleanup completed successfully",
            "deleted_count": deleted_count,
            "days_kept": days,
            "triggered_by": current_user.get("email"),
        }

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to perform cleanup")
