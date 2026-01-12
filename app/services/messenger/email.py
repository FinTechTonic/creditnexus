"""Base messenger interface for sending verification links."""

from abc import ABC, abstractmethod
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class MessengerInterface(ABC):
    """Abstract base class for messenger integrations."""

    @abstractmethod
    async def send_message(
        self, recipient: str, subject: str, message: str, link: Optional[str] = None
    ) -> bool:
        """Send a message with optional verification link.

        Args:
            recipient: Recipient identifier (email, phone, webhook, etc.)
            subject: Message subject/title
            message: Message body
            link: Optional verification link to include

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate messenger configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass


class EmailMessenger(MessengerInterface):
    """Email messenger implementation using SMTP."""

    def __init__(
        self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str, from_email: str
    ):
        """Initialize email messenger.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: From email address
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email

    async def send_message(
        self, recipient: str, subject: str, message: str, link: Optional[str] = None
    ) -> bool:
        """Send email message."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = recipient
            msg["Subject"] = subject

            body = message

            if link:
                body += f"\n\nVerification Link: {link}"

            msg.attach(MIMEText(body, "plain"))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                server.quit()

            logger.info(f"Email sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate email configuration."""
        if not all(
            [self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password, self.from_email]
        ):
            return False, "Missing required SMTP configuration"
        return True, None


class SlackMessenger(MessengerInterface):
    """Slack messenger implementation using webhooks."""

    def __init__(self, webhook_url: str):
        """Initialize Slack messenger.

        Args:
            webhook_url: Slack incoming webhook URL
        """
        self.webhook_url = webhook_url

    async def send_message(
        self, recipient: str, subject: str, message: str, link: Optional[str] = None
    ) -> bool:
        """Send Slack message via webhook."""
        import aiohttp

        try:
            payload = {
                "text": f"*{subject}*\n\n{message}",
                "username": "CreditNexus",
                "icon_emoji": ":shield:",
            }

            if link:
                payload["attachments"] = [
                    {
                        "text": f"Verification Link: {link}",
                        "color": "#36a64f",
                        "actions": [
                            {
                                "type": "button",
                                "text": "Open Verification",
                                "url": link,
                                "style": "primary",
                            }
                        ],
                    }
                ]

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack message sent to {recipient}")
                        return True
                    else:
                        logger.error(f"Slack webhook failed: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate Slack configuration."""
        if not self.webhook_url:
            return False, "Missing Slack webhook URL"
        if not self.webhook_url.startswith("https://hooks.slack.com"):
            return False, "Invalid Slack webhook URL"
        return True, None


class TeamsMessenger(MessengerInterface):
    """Microsoft Teams messenger implementation using webhooks."""

    def __init__(self, webhook_url: str):
        """Initialize Teams messenger.

        Args:
            webhook_url: Teams incoming webhook URL
        """
        self.webhook_url = webhook_url

    async def send_message(
        self, recipient: str, subject: str, message: str, link: Optional[str] = None
    ) -> bool:
        """Send Teams message via webhook."""
        import aiohttp

        try:
            payload = {"summary": subject, "text": message}

            if link:
                payload["potentialAction"] = [
                    {
                        "@type": "OpenUri",
                        "name": "Open Verification",
                        "targets": [{"os": "default", "uri": link}],
                    }
                ]

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, json=payload, headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Teams message sent to {recipient}")
                        return True
                    else:
                        logger.error(f"Teams webhook failed: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Teams message: {e}")
            return False

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate Teams configuration."""
        if not self.webhook_url:
            return False, "Missing Teams webhook URL"
        return True, None


class WhatsAppMessenger(MessengerInterface):
    """WhatsApp messenger implementation using Twilio API."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """Initialize WhatsApp messenger.

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send_message(
        self, recipient: str, subject: str, message: str, link: Optional[str] = None
    ) -> bool:
        """Send WhatsApp message via Twilio."""
        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)

            body = message

            if link:
                body += f"\n\nVerification Link: {link}"

            message = client.messages.create(
                from_=f"whatsapp:{self.from_number}", body=body, to=f"whatsapp:{recipient}"
            )

            logger.info(f"WhatsApp message sent to {recipient}: {message.sid}")
            return True

        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate WhatsApp configuration."""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            return False, "Missing required Twilio configuration"
        return True, None
