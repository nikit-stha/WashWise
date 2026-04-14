from __future__ import annotations

import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import List
from datetime import datetime, timedelta, timezone
import secrets
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.extensions import db, app


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


class Staff(UserMixin, db.Model):
    __tablename__ = "staff"

    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    name: so.Mapped[str] = so.mapped_column(
        sa.String(64),
        nullable=False
    )

    email: so.Mapped[str] = so.mapped_column(
        sa.String(120),
        unique=True,
        nullable=False
    )

    password_hash: so.Mapped[str] = so.mapped_column(
        sa.String(256),
        nullable=False
    )

    is_email_verified: so.Mapped[bool] = so.mapped_column(
        sa.Boolean,
        default=False,
        nullable=False,
    )

    email_verification_otp_hash: so.Mapped[str | None] = so.mapped_column(
        sa.String(256),
        nullable=True,
    )

    email_verification_otp_expires_at: so.Mapped[datetime | None] = so.mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    deposits: so.Mapped[List["Deposit"]] = so.relationship(
        back_populates="staff",
        cascade="all, delete-orphan"
    )

    def get_id(self):
        return str(self.id)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def generate_email_verification_otp(self) -> str:
        otp = f"{secrets.randbelow(1_000_000):06d}"
        self.email_verification_otp_hash = generate_password_hash(otp)
        self.email_verification_otp_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=app.config["EMAIL_VERIFICATION_OTP_EXPIRES"]
        )
        return otp

    def verify_email_otp(self, otp: str) -> bool:
        expires_at = _as_utc(self.email_verification_otp_expires_at)

        if (
            not self.email_verification_otp_hash
            or expires_at is None
            or datetime.now(timezone.utc) > expires_at
        ):
            return False

        return check_password_hash(self.email_verification_otp_hash, otp)

    def mark_email_verified(self):
        self.is_email_verified = True
        self.email_verification_otp_hash = None
        self.email_verification_otp_expires_at = None

    def get_reset_password_token(self) -> str:
        serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        return serializer.dumps(
            {"reset_staff_password": self.id},
            salt="staff-password-reset-salt"
        )

    @staticmethod
    def verify_reset_password_token(token: str):
        serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

        try:
            data = serializer.loads(
                token,
                salt="staff-password-reset-salt",
                max_age=app.config["PASSWORD_RESET_TOKEN_EXPIRES"]
            )
        except (BadSignature, SignatureExpired):
            return None

        staff_id = data.get("reset_staff_password")
        if not staff_id:
            return None

        return db.session.get(Staff, staff_id)

    def __repr__(self):
        return f"<Staff {self.id} - {self.email}>"
