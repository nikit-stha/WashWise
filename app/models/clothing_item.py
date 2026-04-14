from __future__ import annotations

import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import Optional

from app.extensions import db


class ClothingItem(db.Model):
    __tablename__ = "clothing_item"

    id: so.Mapped[int] = so.mapped_column(primary_key=True, index=True)

    deposit_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey("deposit.id"),
        index=True,
        nullable=False
    )

    description: so.Mapped[str] = so.mapped_column(
        sa.String(500),
        nullable=False
    )

    image_filename: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(255)
    )

    deposit: so.Mapped["Deposit"] = so.relationship(
        back_populates="items"
    )