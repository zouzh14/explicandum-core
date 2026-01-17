"""
Unified Email Service

This module provides a centralized email service for the entire application,
including user verification emails and monitoring alerts.
"""

import resend
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from jinja2 import Template

from app.core.config import settings
from app.monitoring.risk_detector import RiskEvent, RiskLevel, RiskType

logger = logging.getLogger(__name__)


class EmailService:
    """Unified email service for all application email needs"""

    def __init__(self):
        """Initialize the email service"""
        self.resend_client = resend
        self.resend_client.api_key = settings.RESEND_API_KEY
        self.from_email = f"Explicandum System <noreply@{settings.MAIL_DOMAIN}>"
        self.alert_email = settings.ALERT_EMAIL
        self.cc_email = settings.CC_EMAIL
        self.skip_sending = settings.SKIP_EMAIL_SENDING

    async def send_verification_code(self, email: str, code: str) -> Dict[str, Any]:
        """
        Send verification code email for user registration

        Args:
            email: Recipient email address
            code: Verification code

        Returns:
            Send result with status and message
        """
        if self.skip_sending:
            logger.info(f"TEST MODE: Verification code for {email}: {code}")
            return {
                "status": "success",
                "message": "Code generated (test mode)",
                "test_code": code,
            }

        try:
            html_template = self._get_verification_template(code)

            params = {
                "from": self.from_email,
                "to": email,
                "subject": f"{code} is your Explicandum verification code",
                "html": html_template,
            }

            response = self.resend_client.Emails.send(params)
            logger.info(f"Verification code sent to {email}: {response}")

            return {"status": "success", "message": "Code sent", "response": response}

        except Exception as e:
            logger.error(f"Failed to send verification code to {email}: {str(e)}")
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}

    async def send_critical_alert(self, risks: List[RiskEvent]) -> bool:
        """
        Send critical security alert email

        Args:
            risks: List of critical risk events

        Returns:
            True if sent successfully, False otherwise
        """
        if not risks:
            return True

        try:
            html_content = self._get_critical_alert_template(risks)

            params = {
                "from": self.from_email,
                "to": self.alert_email,
                "subject": f"🚨 CRITICAL: {len(risks)} Security Risk(s) Detected",
                "html": html_content,
            }

            # Add CC if configured
            if self.cc_email:
                params["bcc"] = [self.cc_email]

            response = self.resend_client.Emails.send(params)
            logger.info(f"Critical alert sent: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send critical alert: {str(e)}")
            return False

    async def send_daily_report(self, risk_stats: Dict[str, Any]) -> bool:
        """
        Send daily security report

        Args:
            risk_stats: Daily risk statistics

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            html_content = self._get_daily_report_template(risk_stats)

            params = {
                "from": self.from_email,
                "to": self.alert_email,
                "subject": f"📊 Daily Security Report - {datetime.now().strftime('%Y-%m-%d')}",
                "html": html_content,
            }

            # Add CC if configured
            if self.cc_email:
                params["bcc"] = [self.cc_email]

            response = self.resend_client.Emails.send(params)
            logger.info(f"Daily report sent: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send daily report: {str(e)}")
            return False

    async def send_test_email(self, test_type: str = "basic") -> bool:
        """
        Send test email to verify email configuration

        Args:
            test_type: Type of test email (basic, critical_alert, daily_report)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if test_type == "basic":
                html_content = self._get_basic_test_template()
                subject = "✅ Explicandum Email Service Test"
            elif test_type == "critical_alert":
                # Create a fake critical risk for testing
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
                    metadata={"test": True},
                )
                html_content = self._get_critical_alert_template([test_risk])
                subject = "🚨 TEST: Critical Security Alert"
            elif test_type == "daily_report":
                test_stats = {
                    "total_risks": 0,
                    "unresolved_risks": 0,
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0,
                    "period_hours": 24,
                }
                html_content = self._get_daily_report_template(test_stats)
                subject = "📊 TEST: Daily Security Report"
            else:
                logger.error(f"Invalid test type: {test_type}")
                return False

            params = {
                "from": self.from_email,
                "to": self.alert_email,
                "subject": subject,
                "html": html_content,
            }

            # Add CC if configured
            if self.cc_email:
                params["bcc"] = [self.cc_email]

            response = self.resend_client.Emails.send(params)
            logger.info(f"Test email sent: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send test email: {str(e)}")
            return False

    def get_email_status(self) -> Dict[str, Any]:
        """
        Get email service configuration status

        Returns:
            Email service status information
        """
        return {
            "configured": bool(settings.RESEND_API_KEY),
            "api_key_configured": bool(settings.RESEND_API_KEY),
            "from_email": self.from_email,
            "alert_email": self.alert_email,
            "cc_email": self.cc_email,
            "service_provider": "Resend",
            "skip_sending": self.skip_sending,
        }

    def _get_verification_template(self, code: str) -> str:
        """Get verification code email template"""
        template_str = """
        <div style="font-family: sans-serif; padding: 20px; color: #18181b; max-width: 600px; margin: 0 auto;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #18181b; margin: 0;">Explicandum</h1>
                <p style="color: #71717a; margin: 5px 0;">Verification Code</p>
            </div>
            
            <div style="background: #f4f4f5; padding: 30px; border-radius: 12px; text-align: center; margin: 20px 0;">
                <p style="margin: 0 0 15px 0; color: #52525b;">Your verification code is:</p>
                <div style="background: #18181b; color: white; padding: 20px; font-size: 32px; font-weight: bold; letter-spacing: 8px; border-radius: 8px; display: inline-block;">
                    {{ code }}
                </div>
            </div>
            
            <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #991b1b; font-size: 14px;">
                    <strong>Security Notice:</strong> This code will expire in 5 minutes. 
                    Never share this code with anyone.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    If you didn't request this code, please ignore this email.
                </p>
            </div>
        </div>
        """

        template = Template(template_str)
        return template.render(code=code)

    def _get_critical_alert_template(self, risks: List[RiskEvent]) -> str:
        """Get critical alert email template"""
        risk_items = ""
        for risk in risks:
            actions_html = ""
            if risk.actions:
                actions_html = "<p style='color: #52525b; margin: 10px 0 0 0;'><strong>Recommended Actions:</strong></p><ul style='margin: 5px 0; padding-left: 20px;'>"
                for action in risk.actions:
                    actions_html += f"<li style='color: #52525b;'>{action}</li>"
                actions_html += "</ul>"

            risk_items += f"""
            <div style="border-left: 4px solid #dc2626; padding: 15px; margin: 15px 0; background: #fef2f2;">
                <h3 style="color: #dc2626; margin: 0 0 10px 0;">{risk.title}</h3>
                <p style="color: #52525b; margin: 5px 0;"><strong>Description:</strong> {risk.description}</p>
                <p style="color: #52525b; margin: 5px 0;"><strong>Value:</strong> {risk.value} (Threshold: {risk.threshold})</p>
                <p style="color: #52525b; margin: 5px 0;"><strong>Time:</strong> {risk.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
                {actions_html}
            </div>
            """

        template_str = f"""
        <div style="font-family: sans-serif; padding: 20px; color: #18181b; max-width: 600px; margin: 0 auto;">
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="background: #dc2626; color: white; padding: 10px 20px; border-radius: 8px; display: inline-block;">
                    🚨 CRITICAL SECURITY ALERT
                </div>
                <h1 style="color: #18181b; margin: 10px 0;">Explicandum Security Monitor</h1>
            </div>
            
            <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #991b1b; font-size: 16px;">
                    <strong>Immediate Attention Required!</strong><br>
                    {len(risks)} critical security risk(s) have been detected in the system.
                </p>
            </div>
            
            <h2 style="color: #18181b; margin: 20px 0 10px 0;">Detected Risks:</h2>
            {risk_items}
            
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #18181b; margin: 0 0 10px 0;">Next Steps:</h3>
                <ol style="margin: 0; padding-left: 20px; color: #52525b;">
                    <li>Review the identified risks above</li>
                    <li>Implement the recommended actions</li>
                    <li>Monitor system for additional anomalies</li>
                    <li>Update security protocols if needed</li>
                </ol>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="#" style="background: #18181b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Security Dashboard
                </a>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    This is an automated security alert from Explicandum System.
                </p>
            </div>
        </div>
        """

        return template_str

    def _get_daily_report_template(self, stats: Dict[str, Any]) -> str:
        """Get daily report email template"""
        template_str = """
        <div style="font-family: sans-serif; padding: 20px; color: #18181b; max-width: 600px; margin: 0 auto;">
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="background: #3b82f6; color: white; padding: 10px 20px; border-radius: 8px; display: inline-block;">
                    📊 Daily Security Report
                </div>
                <h1 style="color: #18181b; margin: 10px 0;">Explicandum System Status</h1>
                <p style="color: #71717a; margin: 5px 0;">{{ report_date }}</p>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0;">
                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #18181b;">{{ total_risks }}</div>
                    <div style="color: #71717a;">Total Risks</div>
                </div>
                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #dc2626;">{{ unresolved_risks }}</div>
                    <div style="color: #71717a;">Unresolved</div>
                </div>
            </div>
            
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #18181b; margin: 0 0 15px 0;">Risk Breakdown:</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 12px; height: 12px; background: #dc2626; border-radius: 50%; margin-right: 8px;"></div>
                        <span style="color: #52525b;">Critical: {{ critical_count }}</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 12px; height: 12px; background: #f59e0b; border-radius: 50%; margin-right: 8px;"></div>
                        <span style="color: #52525b;">High: {{ high_count }}</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 12px; height: 12px; background: #3b82f6; border-radius: 50%; margin-right: 8px;"></div>
                        <span style="color: #52525b;">Medium: {{ medium_count }}</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 12px; height: 12px; background: #10b981; border-radius: 50%; margin-right: 8px;"></div>
                        <span style="color: #52525b;">Low: {{ low_count }}</span>
                    </div>
                </div>
            </div>
            
            {% if critical_count > 0 or high_count > 0 %}
            <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #991b1b;">
                    <strong>⚠️ Attention Required:</strong> {{ critical_count + high_count }} high-priority risks need immediate attention.
                </p>
            </div>
            {% endif %}
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="#" style="background: #18181b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Full Dashboard
                </a>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    This is an automated daily report from Explicandum Security Monitor.<br>
                    Report covers the last {{ period_hours }} hours.
                </p>
            </div>
        </div>
        """

        template = Template(template_str)
        return template.render(
            report_date=datetime.now().strftime("%B %d, %Y"), **stats
        )

    def _get_basic_test_template(self) -> str:
        """Get basic test email template"""
        template_str = """
        <div style="font-family: sans-serif; padding: 20px; color: #18181b; max-width: 600px; margin: 0 auto;">
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="background: #10b981; color: white; padding: 10px 20px; border-radius: 8px; display: inline-block;">
                    ✅ Email Service Test
                </div>
                <h1 style="color: #18181b; margin: 10px 0;">Explicandum System</h1>
            </div>
            
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #166534; font-size: 16px;">
                    <strong>Success!</strong><br>
                    The Explicandum email service is working correctly.
                </p>
            </div>
            
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #18181b; margin: 0 0 10px 0;">Test Details:</h3>
                <ul style="margin: 0; padding-left: 20px; color: #52525b;">
                    <li>Service Provider: Resend</li>
                    <li>From Email: {{ from_email }}</li>
                    <li>Test Time: {{ test_time }}</li>
                    <li>Status: Operational</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    This is a test email from Explicandum System.
                </p>
            </div>
        </div>
        """

        template = Template(template_str)
        return template.render(
            from_email=self.from_email,
            test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


# Global email service instance
email_service = EmailService()
