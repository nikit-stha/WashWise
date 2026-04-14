from flask import current_app, render_template

from app.utils.email_utils import send_email


def send_user_password_reset_email(user):
    token = user.get_reset_password_token()

    send_email(
        subject="[WashWise] Reset Your Password",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user.email],
        text_body=render_template(
            "email/reset_password.txt",
            user=user,
            token=token
        ),
        html_body=render_template(
            "email/reset_password.html",
            user=user,
            token=token
        ),
    )


def send_user_email_verification_otp_email(user, otp):
    send_email(
        subject="[WashWise] Verify Your Email",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user.email],
        text_body=render_template(
            "email/verify_email.txt",
            recipient=user,
            otp=otp
        ),
        html_body=render_template(
            "email/verify_email.html",
            recipient=user,
            otp=otp
        ),
    )


def send_staff_password_reset_email(staff):
    token = staff.get_reset_password_token()

    send_email(
        subject="[WashWise] Staff Password Reset",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[staff.email],
        text_body=render_template(
            "email/staff_reset_password.txt",
            staff=staff,
            token=token
        ),
        html_body=render_template(
            "email/staff_reset_password.html",
            staff=staff,
            token=token
        ),
    )


def send_staff_email_verification_otp_email(staff, otp):
    send_email(
        subject="[WashWise] Verify Staff Email",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[staff.email],
        text_body=render_template(
            "email/staff_verify_email.txt",
            recipient=staff,
            otp=otp
        ),
        html_body=render_template(
            "email/staff_verify_email.html",
            recipient=staff,
            otp=otp
        ),
    )
