from flask import current_app
from flask_mail import Message

from app.extensions import mail


class MailConfigurationError(RuntimeError):
    pass


def get_missing_mail_settings():
    config = current_app.config
    required_settings = ("MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_DEFAULT_SENDER")
    return [setting for setting in required_settings if not config.get(setting)]


def send_email(subject, sender, recipients, text_body, html_body):
    missing_settings = get_missing_mail_settings()
    if missing_settings:
        raise MailConfigurationError(
            "Email is not configured. Set "
            + ", ".join(missing_settings)
            + " in your .env or hosting environment."
        )

    msg = Message(
        subject=subject,
        sender=sender,
        recipients=recipients
    )

    msg.body = text_body
    msg.html = html_body

    mail.send(msg)
