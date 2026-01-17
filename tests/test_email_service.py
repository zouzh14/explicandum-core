"""
Tests for Unified Email Service

This module tests the unified email service functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.services.email_service import EmailService
from app.monitoring.risk_detector import RiskEvent, RiskLevel, RiskType


class TestEmailService:
    """Test cases for EmailService"""

    @pytest.fixture
    def email_service(self):
        """Create email service instance for testing"""
        return EmailService()

    @pytest.fixture
    def sample_risks(self):
        """Create sample risk events for testing"""
        return [
            RiskEvent(
                id="risk_1",
                type=RiskType.SECURITY,
                level=RiskLevel.CRITICAL,
                title="Critical Security Risk",
                description="A critical security vulnerability detected",
                value=95.0,
                threshold=90.0,
                timestamp=datetime.now(),
                actions=["Immediate investigation required", "Patch system"],
                metadata={"source": "security_scan"},
            ),
            RiskEvent(
                id="risk_2",
                type=RiskType.RESOURCE,
                level=RiskLevel.HIGH,
                title="High Resource Usage",
                description="System resources are critically high",
                value=85.0,
                threshold=80.0,
                timestamp=datetime.now(),
                actions=["Scale resources", "Optimize usage"],
                metadata={"source": "resource_monitor"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_send_verification_code_success(self, email_service):
        """Test sending verification code successfully"""
        # Mock the resend service
        with patch("app.services.email_service.resend") as mock_resend:
            mock_resend.Emails.send = AsyncMock(return_value={"id": "email_123"})

            result = await email_service.send_verification_code(
                "test@example.com", "123456"
            )

            assert result["status"] == "success"
            assert (
                "test_code" not in result
            )  # Should not include test code in normal mode
            mock_resend.Emails.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_verification_code_test_mode(self, email_service):
        """Test sending verification code in test mode"""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.SKIP_EMAIL_SENDING = True

            result = await email_service.send_verification_code(
                "test@example.com", "123456"
            )

            assert result["status"] == "success"
            assert result["test_code"] == "123456"

    @pytest.mark.asyncio
    async def test_send_verification_code_failure(self, email_service):
        """Test sending verification code with failure"""
        # Mock resend to raise exception
        with patch("app.services.email_service.resend") as mock_resend:
            mock_resend.Emails.send = AsyncMock(
                side_effect=Exception("SMTP server error")
            )

            result = await email_service.send_verification_code(
                "test@example.com", "123456"
            )

            assert result["status"] == "error"
            assert "Failed to send email" in result["message"]

    @pytest.mark.asyncio
    async def test_send_critical_alert_success(self, email_service, sample_risks):
        """Test sending critical alert successfully"""
        with patch("app.services.email_service.resend") as mock_resend:
            mock_resend.Emails.send = AsyncMock(return_value={"id": "email_123"})

            result = await email_service.send_critical_alert(sample_risks)

            assert result is True
            mock_resend.Emails.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_critical_alert_empty_risks(self, email_service):
        """Test sending critical alert with no risks"""
        result = await email_service.send_critical_alert([])

        assert result is True  # Should return True for empty risks

    @pytest.mark.asyncio
    async def test_send_daily_report_success(self, email_service):
        """Test sending daily report successfully"""
        with patch("app.services.email_service.resend") as mock_resend:
            mock_resend.Emails.send = AsyncMock(return_value={"id": "email_456"})

            stats = {
                "total_risks": 5,
                "unresolved_risks": 2,
                "critical_count": 1,
                "high_count": 1,
                "medium_count": 2,
                "low_count": 1,
                "period_hours": 24,
            }

            result = await email_service.send_daily_report(stats)

            assert result is True
            mock_resend.Emails.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_email_basic(self, email_service):
        """Test sending basic test email"""
        with patch("app.services.email_service.resend") as mock_resend:
            mock_resend.Emails.send = AsyncMock(return_value={"id": "test_email_123"})

            result = await email_service.send_test_email("basic")

            assert result is True
            mock_resend.Emails.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_email_critical_alert(self, email_service):
        """Test sending critical alert test email"""
        with patch("app.services.email_service.resend") as mock_resend:
            mock_resend.Emails.send = AsyncMock(return_value={"id": "test_email_456"})

            result = await email_service.send_test_email("critical_alert")

            assert result is True
            mock_resend.Emails.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_email_daily_report(self, email_service):
        """Test sending daily report test email"""
        with patch("app.services.email_service.resend") as mock_resend:
            mock_resend.Emails.send = AsyncMock(return_value={"id": "test_email_789"})

            result = await email_service.send_test_email("daily_report")

            assert result is True
            mock_resend.Emails.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_email_invalid_type(self, email_service):
        """Test sending test email with invalid type"""
        result = await email_service.send_test_email("invalid_type")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_test_email_failure(self, email_service):
        """Test sending test email with failure"""
        with patch("app.services.email_service.resend") as mock_resend:
            mock_resend.Emails.send = AsyncMock(
                side_effect=Exception("SMTP server error")
            )

            result = await email_service.send_test_email("basic")

            assert result is False

    def test_get_email_status_configured(self, email_service):
        """Test getting email service status when configured"""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = "test_key"
            mock_settings.MAIL_DOMAIN = "example.com"
            mock_settings.ALERT_EMAIL = "admin@example.com"
            mock_settings.CC_EMAIL = "cc@example.com"
            mock_settings.SKIP_EMAIL_SENDING = False

            status = email_service.get_email_status()

            assert status["configured"] is True
            assert status["api_key_configured"] is True
            assert status["from_email"] == "Explicandum System <noreply@example.com>"
            assert status["alert_email"] == "admin@example.com"
            assert status["cc_email"] == "cc@example.com"
            assert status["service_provider"] == "Resend"

    def test_get_email_status_not_configured(self, email_service):
        """Test getting email service status when not configured"""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = None
            mock_settings.MAIL_DOMAIN = "example.com"
            mock_settings.ALERT_EMAIL = "admin@example.com"
            mock_settings.CC_EMAIL = "cc@example.com"

            status = email_service.get_email_status()

            assert status["configured"] is False
            assert status["api_key_configured"] is False

    def test_verification_template_rendering(self, email_service):
        """Test verification code email template rendering"""
        html = email_service._get_verification_template("123456")

        assert "123456" in html
        assert "Explicandum" in html
        assert "Verification Code" in html
        assert "5 minutes" in html

    def test_critical_alert_template_rendering(self, email_service, sample_risks):
        """Test critical alert email template rendering"""
        html = email_service._get_critical_alert_template(sample_risks)

        assert "CRITICAL SECURITY ALERT" in html
        assert "Critical Security Risk" in html
        assert "High Resource Usage" in html
        assert "Immediate investigation required" in html

    def test_daily_report_template_rendering(self, email_service):
        """Test daily report email template rendering"""
        stats = {
            "total_risks": 5,
            "unresolved_risks": 2,
            "critical_count": 1,
            "high_count": 1,
            "medium_count": 2,
            "low_count": 1,
            "period_hours": 24,
        }

        html = email_service._get_daily_report_template(stats)

        assert "Daily Security Report" in html
        assert "5" in html  # total risks
        assert "2" in html  # unresolved risks
        assert "24 hours" in html

    def test_basic_test_template_rendering(self, email_service):
        """Test basic test email template rendering"""
        html = email_service._get_basic_test_template()

        assert "Email Service Test" in html
        assert "Success" in html
        assert "Operational" in html
        assert email_service.from_email in html


class TestEmailServiceIntegration:
    """Test cases for email service integration"""

    @pytest.mark.asyncio
    async def test_email_service_integration(self):
        """Test email service integration with monitoring components"""
        from app.services.email_service import email_service
        from app.monitoring.alert_manager import alert_manager

        # Verify that alert_manager uses the unified email service
        assert alert_manager.email_service is email_service

        # Test email service status
        status = email_service.get_email_status()
        assert "configured" in status
        assert "service_provider" in status
        assert status["service_provider"] == "Resend"

    @pytest.mark.asyncio
    async def test_email_service_api_compatibility(self):
        """Test that email service API is compatible with monitoring components"""
        from app.services.email_service import email_service
        from app.monitoring.risk_detector import RiskEvent, RiskLevel, RiskType
        from datetime import datetime

        # Create test risk
        test_risk = RiskEvent(
            id="test_risk",
            type=RiskType.SECURITY,
            level=RiskLevel.CRITICAL,
            title="Test Risk",
            description="Test description",
            value=1.0,
            threshold=0.0,
            timestamp=datetime.now(),
            actions=["Test action"],
            metadata={"test": True},
        )

        # Test that all required methods exist and can be called
        assert hasattr(email_service, "send_critical_alert")
        assert hasattr(email_service, "send_daily_report")
        assert hasattr(email_service, "send_test_email")
        assert hasattr(email_service, "get_email_status")

        # Test method signatures
        assert callable(email_service.send_critical_alert)
        assert callable(email_service.send_daily_report)
        assert callable(email_service.send_test_email)
        assert callable(email_service.get_email_status)


if __name__ == "__main__":
    pytest.main([__file__])
