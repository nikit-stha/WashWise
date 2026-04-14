from __future__ import annotations

import sqlalchemy as sa
import sqlalchemy.orm as so

from app.extensions import db


class ServiceDetail(db.Model):
    __tablename__ = "service_detail"

    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    deposit_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey("deposit.id"),
        unique=True,
        index=True,
        nullable=False
    )

    item_count: so.Mapped[int] = so.mapped_column(
        nullable=False
    )

    deposit: so.Mapped["Deposit"] = so.relationship(
        back_populates="service"
    )
