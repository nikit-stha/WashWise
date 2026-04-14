from datetime import datetime, timedelta, timezone
from typing import Optional, List
import secrets

import sqlalchemy as sa
import sqlalchemy.orm as so
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


class User(UserMixin, db.Model):
    __tablename__ = "user"

    # Unique address like XK-0001
    user_id: so.Mapped[str] = so.mapped_column(primary_key=True)

    username: so.Mapped[str] = so.mapped_column(
        sa.String(64),
        unique=True,
        index=True,
        nullable=False
    )

    email: so.Mapped[str] = so.mapped_column(
        sa.String(120),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash: so.Mapped[str] = so.mapped_column(
        sa.String(256),
        nullable=False
    )

    hostel_number: so.Mapped[str] = so.mapped_column(
        sa.String(20),
        nullable=False
    )

    created_at: so.Mapped[datetime] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    is_email_verified: so.Mapped[bool] = so.mapped_column(
        sa.Boolean,
        default=False,
        nullable=False,
    )

    email_verification_otp_hash: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(256),
        nullable=True,
    )

    email_verification_otp_expires_at: so.Mapped[Optional[datetime]] = so.mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    deposits: so.Mapped[List["Deposit"]] = so.relationship(
        back_populates="student",
        cascade="all, delete-orphan"
    )

    wardrobe_items: so.Mapped[List["WardrobeItem"]] = so.relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def get_id(self):
        return str(self.user_id)

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
            {"reset_password": self.user_id},
            salt="password-reset-salt"
        )

    @staticmethod
    def verify_reset_password_token(token: str):
        serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

        try:
            data = serializer.loads(
                token,
                salt="password-reset-salt",
                max_age=app.config["PASSWORD_RESET_TOKEN_EXPIRES"]
            )
        except (BadSignature, SignatureExpired):
            return None

        user_id = data.get("reset_password")
        if not user_id:
            return None

        return db.session.get(User, user_id)

    def __repr__(self):
        return f"<User {self.user_id} - {self.username}>"
