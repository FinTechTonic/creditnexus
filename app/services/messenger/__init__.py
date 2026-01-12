"""Messenger package."""

from app.services.messenger.email import (
    MessengerInterface,
    EmailMessenger,
    SlackMessenger,
    TeamsMessenger,
    WhatsAppMessenger,
)
from app.services.messenger.factory import create_messenger, send_verification_link

__all__ = [
    "MessengerInterface",
    "EmailMessenger",
    "SlackMessenger",
    "TeamsMessenger",
    "WhatsAppMessenger",
    "create_messenger",
    "send_verification_link",
]
