"""
Security Risk Detection Module

This module implements comprehensive risk detection logic for the Explicandum system.
It monitors various security metrics and identifies potential threats.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.database.base import get_db
from app.database.models import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(Enum):
    """Risk categories"""

    SECURITY = "security"
    PERFORMANCE = "performance"
    USAGE = "usage"
    SYSTEM = "system"


class RiskEvent:
    """Represents a detected security risk event"""

    def __init__(
        self,
        id: str,
        type: RiskType,
        level: RiskLevel,
        title: str,
        description: str,
        value: float,
        threshold: float,
        timestamp: datetime,
        resolved: bool = False,
        actions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.type = type
        self.level = level
        self.title = title
        self.description = description
        self.value = value
        self.threshold = threshold
        self.timestamp = timestamp
        self.resolved = resolved
        self.actions = actions or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "actions": self.actions,
            "metadata": self.metadata,
        }


class RiskDetector:
    """Main risk detection engine"""

    def __init__(self):
        self.risk_thresholds = {
            "quota_exhaustion_threshold": 0.9,  # 90% quota usage
            "unusual_activity_threshold": 0.8,  # 80% active users
            "admin_inactivity_days": 7,  # 7 days admin inactivity
            "high_usage_threshold": 50000,  # 50k avg tokens per user
            "new_users_surge_threshold": 10,  # 10 new users in 1 hour
            "same_ip_registration_threshold": 3,  # 3 users from same IP
        }

    def detect_all_risks(self, db: Session) -> List[RiskEvent]:
        """Run all risk detection checks"""
        risks = []

        try:
            # 1. User quota exhaustion risk
            quota_risks = self.detect_quota_exhaustion_risks(db)
            risks.extend(quota_risks)

            # 2. Unusual activity patterns
            activity_risks = self.detect_unusual_activity_risks(db)
            risks.extend(activity_risks)

            # 3. Admin account security
            admin_risks = self.detect_admin_security_risks(db)
            risks.extend(admin_risks)

            # 4. High resource usage
            usage_risks = self.detect_high_usage_risks(db)
            risks.extend(usage_risks)

            # 5. Registration anomalies
            registration_risks = self.detect_registration_anomalies(db)
            risks.extend(registration_risks)

            # 6. IP-based security risks
            ip_risks = self.detect_ip_security_risks(db)
            risks.extend(ip_risks)

            logger.info(f"Risk detection completed: {len(risks)} risks found")

        except Exception as e:
            logger.error(f"Error during risk detection: {str(e)}")
            # Create a system risk for the detection failure
            risks.append(
                RiskEvent(
                    id=f"detection_failure_{datetime.now().timestamp()}",
                    type=RiskType.SYSTEM,
                    level=RiskLevel.HIGH,
                    title="Risk Detection System Failure",
                    description=f"Risk detection system encountered an error: {str(e)}",
                    value=1,
                    threshold=0,
                    timestamp=datetime.now(),
                    actions=["Check system logs", "Restart monitoring service"],
                )
            )

        return risks

    def detect_quota_exhaustion_risks(self, db: Session) -> List[RiskEvent]:
        """Detect users approaching quota limits"""
        risks = []

        try:
            users = db.query(User).all()
            users_near_exhaustion = [
                user
                for user in users
                if user.tokens_used / user.token_quota
                > self.risk_thresholds["quota_exhaustion_threshold"]
            ]

            if users_near_exhaustion:
                risk_level = (
                    RiskLevel.CRITICAL
                    if len(users_near_exhaustion) > 3
                    else RiskLevel.HIGH
                )

                risk = RiskEvent(
                    id=f"quota_exhaustion_{datetime.now().timestamp()}",
                    type=RiskType.USAGE,
                    level=risk_level,
                    title="User Quota Near Exhaustion",
                    description=f"{len(users_near_exhaustion)} users have quota usage over 90%",
                    value=len(users_near_exhaustion),
                    threshold=3,
                    timestamp=datetime.now(),
                    metadata={
                        "affected_users": [user.id for user in users_near_exhaustion],
                        "usage_percentages": [
                            round((user.tokens_used / user.token_quota) * 100, 1)
                            for user in users_near_exhaustion
                        ],
                    },
                    actions=[
                        "Contact administrators to increase quotas",
                        "Review user usage patterns",
                        "Consider implementing automatic quota management",
                    ],
                )
                risks.append(risk)

        except Exception as e:
            logger.error(f"Error detecting quota exhaustion risks: {str(e)}")

        return risks

    def detect_unusual_activity_risks(self, db: Session) -> List[RiskEvent]:
        """Detect unusual user activity patterns"""
        risks = []

        try:
            users = db.query(User).all()
            now = datetime.now()
            recent_threshold = now - timedelta(hours=24)

            # Count active users in last 24 hours
            recent_users = [
                user
                for user in users
                if user.last_request_at and user.last_request_at > recent_threshold
            ]

            if len(users) > 10:  # Only check if we have enough users
                active_ratio = len(recent_users) / len(users)

                if active_ratio > self.risk_thresholds["unusual_activity_threshold"]:
                    risk = RiskEvent(
                        id=f"unusual_activity_{datetime.now().timestamp()}",
                        type=RiskType.SECURITY,
                        level=RiskLevel.MEDIUM,
                        title="Unusual User Activity Pattern",
                        description=f"{round(active_ratio * 100)}% of users active in 24 hours",
                        value=round(active_ratio * 100),
                        threshold=self.risk_thresholds["unusual_activity_threshold"]
                        * 100,
                        timestamp=datetime.now(),
                        metadata={
                            "total_users": len(users),
                            "active_users": len(recent_users),
                            "activity_ratio": active_ratio,
                        },
                        actions=[
                            "Check for potential bot activity",
                            "Review new user registrations",
                            "Analyze login IP patterns",
                        ],
                    )
                    risks.append(risk)

        except Exception as e:
            logger.error(f"Error detecting unusual activity risks: {str(e)}")

        return risks

    def detect_admin_security_risks(self, db: Session) -> List[RiskEvent]:
        """Detect admin account security issues"""
        risks = []

        try:
            admin_users = db.query(User).filter(User.role == "admin").all()

            if not admin_users:
                # No admin users - critical risk
                risk = RiskEvent(
                    id=f"no_admin_users_{datetime.now().timestamp()}",
                    type=RiskType.SECURITY,
                    level=RiskLevel.CRITICAL,
                    title="No Administrator Accounts",
                    description="System has no administrator accounts configured",
                    value=0,
                    threshold=1,
                    timestamp=datetime.now(),
                    actions=[
                        "Create administrator account immediately",
                        "Review user permissions configuration",
                    ],
                )
                risks.append(risk)
                return risks

            # Check for inactive admin accounts
            now = datetime.now()
            inactivity_threshold = now - timedelta(
                days=self.risk_thresholds["admin_inactivity_days"]
            )

            inactive_admins = [
                admin
                for admin in admin_users
                if not admin.last_request_at
                or admin.last_request_at < inactivity_threshold
            ]

            if inactive_admins:
                risk_level = (
                    RiskLevel.CRITICAL
                    if len(inactive_admins) == len(admin_users)
                    else RiskLevel.HIGH
                )

                risk = RiskEvent(
                    id=f"admin_inactivity_{datetime.now().timestamp()}",
                    type=RiskType.SECURITY,
                    level=risk_level,
                    title="Administrator Account Inactivity",
                    description=f"{len(inactive_admins)}/{len(admin_users)} admins inactive for 7+ days",
                    value=len(inactive_admins),
                    threshold=1,
                    timestamp=datetime.now(),
                    metadata={
                        "total_admins": len(admin_users),
                        "inactive_admins": [admin.id for admin in inactive_admins],
                        "last_active_times": [
                            admin.last_request_at.isoformat()
                            if admin.last_request_at
                            else None
                            for admin in inactive_admins
                        ],
                    },
                    actions=[
                        "Contact inactive administrators",
                        "Review admin access logs",
                        "Consider emergency admin access procedures",
                    ],
                )
                risks.append(risk)

        except Exception as e:
            logger.error(f"Error detecting admin security risks: {str(e)}")

        return risks

    def detect_high_usage_risks(self, db: Session) -> List[RiskEvent]:
        """Detect high resource usage patterns"""
        risks = []

        try:
            users = db.query(User).all()

            if len(users) > 0:
                total_tokens_used = sum(user.tokens_used for user in users)
                avg_tokens_per_user = total_tokens_used / len(users)

                if avg_tokens_per_user > self.risk_thresholds["high_usage_threshold"]:
                    risk = RiskEvent(
                        id=f"high_usage_{datetime.now().timestamp()}",
                        type=RiskType.PERFORMANCE,
                        level=RiskLevel.MEDIUM,
                        title="High System Resource Usage",
                        description=f"Average user token usage: {round(avg_tokens_per_user):,}",
                        value=round(avg_tokens_per_user),
                        threshold=self.risk_thresholds["high_usage_threshold"],
                        timestamp=datetime.now(),
                        metadata={
                            "total_tokens": total_tokens_used,
                            "total_users": len(users),
                            "avg_tokens_per_user": avg_tokens_per_user,
                        },
                        actions=[
                            "Optimize AI model usage efficiency",
                            "Consider implementing rate limiting",
                            "Review resource allocation policies",
                        ],
                    )
                    risks.append(risk)

        except Exception as e:
            logger.error(f"Error detecting high usage risks: {str(e)}")

        return risks

    def detect_registration_anomalies(self, db: Session) -> List[RiskEvent]:
        """Detect unusual registration patterns"""
        risks = []

        try:
            users = db.query(User).all()
            now = datetime.now()
            recent_threshold = now - timedelta(hours=1)

            # Count recent registrations
            recent_registrations = [
                user
                for user in users
                if user.created_at and user.created_at > recent_threshold
            ]

            if (
                len(recent_registrations)
                > self.risk_thresholds["new_users_surge_threshold"]
            ):
                risk = RiskEvent(
                    id=f"registration_surge_{datetime.now().timestamp()}",
                    type=RiskType.SECURITY,
                    level=RiskLevel.HIGH,
                    title="Unusual Registration Spike",
                    description=f"{len(recent_registrations)} new users registered in the last hour",
                    value=len(recent_registrations),
                    threshold=self.risk_thresholds["new_users_surge_threshold"],
                    timestamp=datetime.now(),
                    metadata={
                        "recent_registrations": len(recent_registrations),
                        "registration_ips": list(
                            set(
                                user.registration_ip
                                for user in recent_registrations
                                if user.registration_ip
                            )
                        ),
                    },
                    actions=[
                        "Review new user registrations for authenticity",
                        "Check for potential bot registration patterns",
                        "Consider implementing CAPTCHA or rate limiting",
                    ],
                )
                risks.append(risk)

        except Exception as e:
            logger.error(f"Error detecting registration anomalies: {str(e)}")

        return risks

    def detect_ip_security_risks(self, db: Session) -> List[RiskEvent]:
        """Detect IP-based security risks"""
        risks = []

        try:
            users = db.query(User).all()

            # Count registrations per IP
            ip_registrations = {}
            for user in users:
                if user.registration_ip:
                    ip_registrations[user.registration_ip] = (
                        ip_registrations.get(user.registration_ip, 0) + 1
                    )

            # Find IPs with multiple registrations
            suspicious_ips = {
                ip: count
                for ip, count in ip_registrations.items()
                if count >= self.risk_thresholds["same_ip_registration_threshold"]
            }

            if suspicious_ips:
                for ip, count in suspicious_ips.items():
                    risk = RiskEvent(
                        id=f"ip_security_{ip}_{datetime.now().timestamp()}",
                        type=RiskType.SECURITY,
                        level=RiskLevel.MEDIUM,
                        title="Multiple Registrations from Same IP",
                        description=f"{count} users registered from IP: {ip}",
                        value=count,
                        threshold=self.risk_thresholds[
                            "same_ip_registration_threshold"
                        ],
                        timestamp=datetime.now(),
                        metadata={
                            "ip_address": ip,
                            "registration_count": count,
                            "user_ids": [
                                user.id for user in users if user.registration_ip == ip
                            ],
                        },
                        actions=[
                            "Review user accounts from this IP address",
                            "Check for potential account farming",
                            "Consider IP-based registration limits",
                        ],
                    )
                    risks.append(risk)

        except Exception as e:
            logger.error(f"Error detecting IP security risks: {str(e)}")

        return risks
