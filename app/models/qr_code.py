from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

import sqlalchemy as sa
import sqlalchemy.orm as so

from app.extensions import db


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


class QRCode(db.Model):
    __tablename__ = "qr_code"

    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    deposit_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey("deposit.id"),
        nullable=False,
        index=True
    )

    token: so.Mapped[str] = so.mapped_column(
        sa.String(128),
        unique=True,
        nullable=False,
        index=True
    )

    expires_at: so.Mapped[datetime] = so.mapped_column(
        nullable=False,
        index=True
    )

    is_used: so.Mapped[bool] = so.mapped_column(
        sa.Boolean,
        default=False,
        nullable=False
    )

    deposit: so.Mapped["Deposit"] = so.relationship(
        back_populates="qr_codes"
    )

    def __init__(self, deposit_id: int):
        self.deposit_id = deposit_id
        self.token = secrets.token_urlsafe(32)
        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    def is_expired(self) -> bool:
        expires_at = _as_utc(self.expires_at)
        return expires_at is None or datetime.now(timezone.utc) > expires_at

    def mark_used(self):
        self.is_used = True
