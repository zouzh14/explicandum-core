"""
Alert Management Module

This module manages risk events, including storage, resolution tracking,
and coordination with the email notification service.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .risk_detector import RiskEvent, RiskLevel, RiskType
from app.services.email_service import email_service
from app.database.models import RiskEventRecord

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages risk events and alerts"""

    def __init__(self):
        self.email_service = email_service
        self.auto_email_threshold = (
            RiskLevel.HIGH
        )  # Auto-send emails for HIGH and CRITICAL

    def create_risk_event_record(self, risk: RiskEvent, db: Session) -> RiskEventRecord:
        """Create a database record for a risk event"""
        try:
            import json

            record = RiskEventRecord(
                id=risk.id,
                type=risk.type.value,
                level=risk.level.value,
                title=risk.title,
                description=risk.description,
                value=risk.value,
                threshold=risk.threshold,
                timestamp=risk.timestamp,
                resolved=risk.resolved,
                actions=json.dumps(risk.actions) if risk.actions else None,
                metadata=json.dumps(risk.metadata) if risk.metadata else None,
            )

            db.add(record)
            db.commit()
            db.refresh(record)

            logger.info(f"Created risk event record: {risk.id}")
            return record

        except Exception as e:
            logger.error(f"Error creating risk event record: {str(e)}")
            db.rollback()
            raise

    def store_risk_events(self, risks: List[RiskEvent], db: Session) -> int:
        """Store multiple risk events in the database"""
        stored_count = 0

        for risk in risks:
            try:
                # Check if event already exists
                existing = (
                    db.query(RiskEventRecord)
                    .filter(RiskEventRecord.id == risk.id)
                    .first()
                )

                if not existing:
                    self.create_risk_event_record(risk, db)
                    stored_count += 1

            except Exception as e:
                logger.error(f"Error storing risk event {risk.id}: {str(e)}")
                continue

        logger.info(f"Stored {stored_count} new risk events")
        return stored_count

    def get_unresolved_risks(
        self, db: Session, limit: int = 50
    ) -> List[RiskEventRecord]:
        """Get unresolved risk events"""
        try:
            return (
                db.query(RiskEventRecord)
                .filter(RiskEventRecord.resolved == False)
                .order_by(RiskEventRecord.timestamp.desc())
                .limit(limit)
                .all()
            )

        except Exception as e:
            logger.error(f"Error getting unresolved risks: {str(e)}")
            return []

    def get_risks_by_level(
        self, db: Session, level: RiskLevel, unresolved_only: bool = True
    ) -> List[RiskEventRecord]:
        """Get risks by severity level"""
        try:
            query = db.query(RiskEventRecord).filter(
                RiskEventRecord.level == level.value
            )

            if unresolved_only:
                query = query.filter(RiskEventRecord.resolved == False)

            return query.order_by(RiskEventRecord.timestamp.desc()).all()

        except Exception as e:
            logger.error(f"Error getting risks by level {level}: {str(e)}")
            return []

    def resolve_risk(
        self, risk_id: str, resolved_by: str = "system", db: Session = None
    ) -> bool:
        """Mark a risk event as resolved"""
        if not db:
            from app.database.base import get_db

            db = next(get_db())

        try:
            risk_record = (
                db.query(RiskEventRecord).filter(RiskEventRecord.id == risk_id).first()
            )

            if not risk_record:
                logger.warning(f"Risk event not found: {risk_id}")
                return False

            risk_record.resolved = True
            risk_record.resolved_at = datetime.utcnow()
            risk_record.resolved_by = resolved_by

            db.commit()
            logger.info(f"Resolved risk event: {risk_id} by {resolved_by}")
            return True

        except Exception as e:
            logger.error(f"Error resolving risk {risk_id}: {str(e)}")
            db.rollback()
            return False

    def get_risk_statistics(self, db: Session, hours: int = 24) -> Dict[str, Any]:
        """Get risk statistics for the specified time period"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            # Total risks in period
            total_risks = (
                db.query(RiskEventRecord)
                .filter(RiskEventRecord.timestamp >= since)
                .count()
            )

            # Unresolved risks
            unresolved_risks = (
                db.query(RiskEventRecord)
                .filter(
                    RiskEventRecord.timestamp >= since,
                    RiskEventRecord.resolved == False,
                )
                .count()
            )

            # Risks by level
            risks_by_level = {}
            for level in RiskLevel:
                count = (
                    db.query(RiskEventRecord)
                    .filter(
                        RiskEventRecord.timestamp >= since,
                        RiskEventRecord.level == level.value,
                        RiskEventRecord.resolved == False,
                    )
                    .count()
                )
                risks_by_level[level.value] = count

            # Risks by type
            risks_by_type = {}
            for risk_type in RiskType:
                count = (
                    db.query(RiskEventRecord)
                    .filter(
                        RiskEventRecord.timestamp >= since,
                        RiskEventRecord.type == risk_type.value,
                        RiskEventRecord.resolved == False,
                    )
                    .count()
                )
                risks_by_type[risk_type.value] = count

            return {
                "period_hours": hours,
                "total_risks": total_risks,
                "unresolved_risks": unresolved_risks,
                "resolved_risks": total_risks - unresolved_risks,
                "risks_by_level": risks_by_level,
                "risks_by_type": risks_by_type,
                "critical_count": risks_by_level.get(RiskLevel.CRITICAL.value, 0),
                "high_count": risks_by_level.get(RiskLevel.HIGH.value, 0),
                "medium_count": risks_by_level.get(RiskLevel.MEDIUM.value, 0),
                "low_count": risks_by_level.get(RiskLevel.LOW.value, 0),
            }

        except Exception as e:
            logger.error(f"Error getting risk statistics: {str(e)}")
            return {}

    async def process_new_risks(
        self, risks: List[RiskEvent], db: Session
    ) -> Dict[str, Any]:
        """Process new risk events and send notifications if needed"""
        results = {
            "stored": 0,
            "emails_sent": 0,
            "critical_risks": 0,
            "high_risks": 0,
            "errors": [],
        }

        try:
            # Store risk events
            results["stored"] = self.store_risk_events(risks, db)

            # Count critical and high risks
            results["critical_risks"] = len(
                [r for r in risks if r.level == RiskLevel.CRITICAL]
            )
            results["high_risks"] = len([r for r in risks if r.level == RiskLevel.HIGH])

            # Send email notifications for critical and high risks
            if results["critical_risks"] > 0 or results["high_risks"] > 0:
                email_success = await self.email_service.send_critical_alert(risks)
                if email_success:
                    results["emails_sent"] = 1

                    # Mark email as sent for these risks
                    for risk in risks:
                        if risk.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                            record = (
                                db.query(RiskEventRecord)
                                .filter(RiskEventRecord.id == risk.id)
                                .first()
                            )
                            if record:
                                record.email_sent = True
                                record.email_sent_at = datetime.utcnow()

                    db.commit()
                    logger.info(
                        f"Sent email alert for {results['critical_risks']} critical and {results['high_risks']} high risks"
                    )
                else:
                    results["errors"].append("Failed to send email alert")

        except Exception as e:
            error_msg = f"Error processing new risks: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    async def send_daily_report(self, db: Session) -> bool:
        """Send daily security report"""
        try:
            # Get risks from last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
            recent_risks = (
                db.query(RiskEventRecord)
                .filter(RiskEventRecord.timestamp >= since)
                .all()
            )

            # Convert to RiskEvent objects
            risk_events = []
            for record in recent_risks:
                import json

                risk = RiskEvent(
                    id=record.id,
                    type=RiskType(record.type),
                    level=RiskLevel(record.level),
                    title=record.title,
                    description=record.description,
                    value=record.value,
                    threshold=record.threshold,
                    timestamp=record.timestamp,
                    resolved=record.resolved,
                    actions=json.loads(record.actions) if record.actions else [],
                    metadata=json.loads(record.metadata) if record.metadata else {},
                )
                risk_events.append(risk)

            # Send daily report
            return await self.email_service.send_daily_report(risk_events)

        except Exception as e:
            logger.error(f"Error sending daily report: {str(e)}")
            return False

    def cleanup_old_risks(self, db: Session, days: int = 30) -> int:
        """Clean up old resolved risk events"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            deleted_count = (
                db.query(RiskEventRecord)
                .filter(
                    RiskEventRecord.resolved == True,
                    RiskEventRecord.resolved_at < cutoff_date,
                )
                .delete()
            )

            db.commit()
            logger.info(f"Cleaned up {deleted_count} old risk events")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old risks: {str(e)}")
            db.rollback()
            return 0

    def get_email_service_status(self) -> Dict[str, Any]:
        """Get email service status"""
        return self.email_service.get_email_status()


# Global alert manager instance
alert_manager = AlertManager()
