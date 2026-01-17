"""
Unit tests for alert manager module
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from app.monitoring.alert_manager import AlertManager, RiskEventRecord
from app.monitoring.risk_detector import RiskEvent, RiskLevel, RiskType


class TestAlertManager:
    """Test AlertManager class"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock(spec=Session)

    @pytest.fixture
    def alert_manager(self):
        """Create AlertManager instance"""
        return AlertManager()

    @pytest.fixture
    def sample_risk_event(self):
        """Create a sample risk event"""
        return RiskEvent(
            id="risk_001",
            type=RiskType.USER_QUOTA_EXHAUSTED,
            level=RiskLevel.HIGH,
            title="User Quota Exhausted",
            description="User has exhausted 95% of quota",
            value=95.0,
            threshold=90.0,
            metadata={"user_id": "usr_123"},
        )

    def test_create_risk_event_record(self, alert_manager, mock_db, sample_risk_event):
        """Test creating a risk event record"""
        # Mock database operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        record = alert_manager.create_risk_event_record(sample_risk_event, mock_db)

        # Verify database operations were called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Verify record properties
        assert record.id == sample_risk_event.id
        assert record.type == sample_risk_event.type.value
        assert record.level == sample_risk_event.level.value
        assert record.title == sample_risk_event.title
        assert record.description == sample_risk_event.description
        assert record.value == sample_risk_event.value
        assert record.threshold == sample_risk_event.threshold
        assert record.resolved == sample_risk_event.resolved

    def test_create_risk_event_record_with_metadata(self, alert_manager, mock_db):
        """Test creating a risk event record with metadata and actions"""
        metadata = {"user_id": "usr_123", "quota_used": 95000}
        actions = ["notify_admin", "restrict_access"]

        risk_event = RiskEvent(
            id="risk_002",
            type=RiskType.ADMIN_INACTIVE,
            level=RiskLevel.MEDIUM,
            title="Admin Inactive",
            description="Admin user inactive for 7 days",
            value=7,
            threshold=7,
            actions=actions,
            metadata=metadata,
        )

        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        record = alert_manager.create_risk_event_record(risk_event, mock_db)

        # Verify JSON serialization
        import json

        assert record.actions == json.dumps(actions)
        assert record.event_metadata == json.dumps(metadata)

    def test_store_risk_events_new(self, alert_manager, mock_db, sample_risk_event):
        """Test storing new risk events"""
        # Mock database query to return no existing records
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Mock create_risk_event_record
        alert_manager.create_risk_event_record = Mock(return_value=Mock())

        stored_count = alert_manager.store_risk_events([sample_risk_event], mock_db)

        assert stored_count == 1
        alert_manager.create_risk_event_record.assert_called_once_with(
            sample_risk_event, mock_db
        )

    def test_store_risk_events_existing(
        self, alert_manager, mock_db, sample_risk_event
    ):
        """Test storing existing risk events (should not duplicate)"""
        # Mock database query to return existing record
        existing_record = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = existing_record
        mock_db.query.return_value = mock_query

        # Mock create_risk_event_record
        alert_manager.create_risk_event_record = Mock()

        stored_count = alert_manager.store_risk_events([sample_risk_event], mock_db)

        assert stored_count == 0  # Should not store duplicate
        alert_manager.create_risk_event_record.assert_not_called()

    def test_get_unresolved_risks(self, alert_manager, mock_db):
        """Test getting unresolved risks"""
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            Mock(id="risk_001", resolved=False),
            Mock(id="risk_002", resolved=False),
        ]
        mock_db.query.return_value = mock_query

        risks = alert_manager.get_unresolved_risks(mock_db, limit=50)

        assert len(risks) == 2
        mock_db.query.assert_called_once_with(RiskEventRecord)

    def test_get_risks_by_level(self, alert_manager, mock_db):
        """Test getting risks by level"""
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
            Mock(id="risk_001", level=RiskLevel.HIGH.value, resolved=False),
        ]
        mock_db.query.return_value = mock_query

        risks = alert_manager.get_risks_by_level(
            mock_db, RiskLevel.HIGH, unresolved_only=True
        )

        assert len(risks) == 1
        assert risks[0].level == RiskLevel.HIGH.value

    def test_resolve_risk_success(self, alert_manager, mock_db):
        """Test resolving a risk successfully"""
        # Mock risk record
        risk_record = Mock()
        risk_record.resolved = False
        risk_record.resolved_at = None
        risk_record.resolved_by = None

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = risk_record
        mock_db.query.return_value = mock_query

        success = alert_manager.resolve_risk("risk_001", "admin_user", mock_db)

        assert success is True
        assert risk_record.resolved is True
        assert risk_record.resolved_at is not None
        assert risk_record.resolved_by == "admin_user"
        mock_db.commit.assert_called_once()

    def test_resolve_risk_not_found(self, alert_manager, mock_db):
        """Test resolving a risk that doesn't exist"""
        # Mock database query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        success = alert_manager.resolve_risk("nonexistent_risk", "admin_user", mock_db)

        assert success is False
        mock_db.commit.assert_not_called()

    def test_get_risk_statistics(self, alert_manager, mock_db):
        """Test getting risk statistics"""
        # Mock database queries for statistics
        mock_query = Mock()

        # Mock total risks query
        mock_query.filter.return_value.count.return_value = 10

        # Mock unresolved risks query
        mock_query.filter.return_value.filter.return_value.count.return_value = 3

        mock_db.query.return_value = mock_query

        stats = alert_manager.get_risk_statistics(mock_db, hours=24)

        # Verify statistics structure
        assert "period_hours" in stats
        assert "total_risks" in stats
        assert "unresolved_risks" in stats
        assert "resolved_risks" in stats
        assert "risks_by_level" in stats
        assert "risks_by_type" in stats

        assert stats["period_hours"] == 24
        assert stats["total_risks"] == 10
        assert stats["unresolved_risks"] == 3
        assert stats["resolved_risks"] == 7

    @pytest.mark.asyncio
    async def test_process_new_risks_with_email(
        self, alert_manager, mock_db, sample_risk_event
    ):
        """Test processing new risks with email notification"""
        # Mock dependencies
        alert_manager.store_risk_events = Mock(return_value=1)
        alert_manager.email_service.send_critical_alert = AsyncMock(return_value=True)

        # Mock database query for email marking
        mock_record = Mock()
        mock_record.email_sent = False
        mock_record.email_sent_at = None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_record
        mock_db.query.return_value = mock_query

        # Create high-level risk to trigger email
        high_risk = RiskEvent(
            id="risk_003",
            type=RiskType.USER_QUOTA_EXHAUSTED,
            level=RiskLevel.CRITICAL,
            title="Critical Risk",
            description="Critical risk description",
            value=99.0,
            threshold=95.0,
        )

        results = await alert_manager.process_new_risks([high_risk], mock_db)

        assert results["stored"] == 1
        assert results["critical_risks"] == 1
        assert results["emails_sent"] == 1
        assert len(results["errors"]) == 0

        # Verify email was sent
        alert_manager.email_service.send_critical_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_new_risks_no_email(
        self, alert_manager, mock_db, sample_risk_event
    ):
        """Test processing new risks without email notification"""
        # Mock dependencies
        alert_manager.store_risk_events = Mock(return_value=1)

        results = await alert_manager.process_new_risks([sample_risk_event], mock_db)

        assert results["stored"] == 1
        assert results["critical_risks"] == 0  # Sample risk is HIGH, not CRITICAL
        assert results["high_risks"] == 1
        assert results["emails_sent"] == 0  # No email for HIGH level in this test

    @pytest.mark.asyncio
    async def test_send_daily_report(self, alert_manager, mock_db):
        """Test sending daily report"""
        # Mock recent risk records
        now = datetime.utcnow()
        mock_records = [
            Mock(
                id="risk_001",
                type=RiskType.USER_QUOTA_EXHAUSTED.value,
                level=RiskLevel.HIGH.value,
                title="High Risk",
                description="High risk description",
                value=95.0,
                threshold=90.0,
                timestamp=now - timedelta(hours=12),
                resolved=False,
                actions="[]",
                event_metadata="{}",
            )
        ]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_records
        mock_db.query.return_value = mock_query

        # Mock email service
        alert_manager.email_service.send_daily_report = AsyncMock(return_value=True)

        success = await alert_manager.send_daily_report(mock_db)

        assert success is True
        alert_manager.email_service.send_daily_report.assert_called_once()

    def test_cleanup_old_risks(self, alert_manager, mock_db):
        """Test cleaning up old resolved risks"""
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 5  # 5 records deleted
        mock_db.query.return_value = mock_query

        deleted_count = alert_manager.cleanup_old_risks(mock_db, days=30)

        assert deleted_count == 5
        mock_db.commit.assert_called_once()

    def test_get_email_service_status(self, alert_manager):
        """Test getting email service status"""
        # Mock email service status
        mock_status = {
            "configured": True,
            "from_email": "test@example.com",
            "resend_api_key_configured": True,
        }
        alert_manager.email_service.get_email_status = Mock(return_value=mock_status)

        status = alert_manager.get_email_service_status()

        assert status == mock_status
        alert_manager.email_service.get_email_status.assert_called_once()

    def test_store_risk_events_with_exception(
        self, alert_manager, mock_db, sample_risk_event
    ):
        """Test storing risk events with database exception"""
        # Mock database query to raise exception
        mock_db.query.side_effect = Exception("Database error")

        stored_count = alert_manager.store_risk_events([sample_risk_event], mock_db)

        assert stored_count == 0  # Should return 0 on error

    def test_resolve_risk_with_exception(self, alert_manager, mock_db):
        """Test resolving risk with database exception"""
        # Mock database query to raise exception
        mock_db.query.side_effect = Exception("Database error")

        success = alert_manager.resolve_risk("risk_001", "admin_user", mock_db)

        assert success is False

    def test_get_risk_statistics_with_exception(self, alert_manager, mock_db):
        """Test getting risk statistics with database exception"""
        # Mock database query to raise exception
        mock_db.query.side_effect = Exception("Database error")

        stats = alert_manager.get_risk_statistics(mock_db)

        assert stats == {}  # Should return empty dict on error

    @pytest.mark.asyncio
    async def test_send_daily_report_with_exception(self, alert_manager, mock_db):
        """Test sending daily report with exception"""
        # Mock database query to raise exception
        mock_db.query.side_effect = Exception("Database error")

        success = await alert_manager.send_daily_report(mock_db)

        assert success is False

    def test_cleanup_old_risks_with_exception(self, alert_manager, mock_db):
        """Test cleaning up old risks with database exception"""
        # Mock database operations to raise exception
        mock_db.query.side_effect = Exception("Database error")

        deleted_count = alert_manager.cleanup_old_risks(mock_db, days=30)

        assert deleted_count == 0  # Should return 0 on error

    def test_create_risk_event_record_rollback_on_error(
        self, alert_manager, mock_db, sample_risk_event
    ):
        """Test database rollback on error during record creation"""
        # Mock database operations to raise exception
        mock_db.add = Mock()
        mock_db.commit = Mock(side_effect=Exception("Database error"))
        mock_db.rollback = Mock()

        # Should raise exception
        with pytest.raises(Exception):
            alert_manager.create_risk_event_record(sample_risk_event, mock_db)

        # Verify rollback was called
        mock_db.rollback.assert_called_once()
