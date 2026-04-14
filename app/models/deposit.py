from datetime import datetime, timezone
from typing import Optional, List

import sqlalchemy as sa
import sqlalchemy.orm as so

from app.extensions import db


class Deposit(db.Model):
    __tablename__ = "deposit"
    __table_args__ = (
        sa.Index("ix_deposit_student_created_at", "student_id", "created_at"),
    )

    id: so.Mapped[int] = so.mapped_column(primary_key=True, index=True)

    student_id: so.Mapped[str] = so.mapped_column(
        sa.ForeignKey("user.user_id"),
        index=True,
        nullable=False
    )

    staff_id: so.Mapped[Optional[int]] = so.mapped_column(
        sa.ForeignKey("staff.id"),
        index=True
    )

    status: so.Mapped[str] = so.mapped_column(
        sa.String(20),
        default="Not Given",
        nullable=False
    )

    created_at: so.Mapped[datetime] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False
    )

    # ------------------ RELATIONSHIPS ------------------ #
    student: so.Mapped["User"] = so.relationship(
        back_populates="deposits"
    )

    staff: so.Mapped[Optional["Staff"]] = so.relationship(
        back_populates="deposits"
    )

    items: so.Mapped[list["ClothingItem"]] = so.relationship(
        back_populates="deposit",
        cascade="all, delete-orphan"
    )

    service: so.Mapped[Optional["ServiceDetail"]] = so.relationship(
        back_populates="deposit",
        uselist=False,
        cascade="all, delete-orphan"
    )

    qr_codes: so.Mapped[List["QRCode"]] = so.relationship(
        back_populates="deposit",
        cascade="all, delete-orphan"
    )
