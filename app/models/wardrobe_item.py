from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.orm as so

from app.extensions import db


class WardrobeItem(db.Model):
    __tablename__ = "wardrobe_item"
    __table_args__ = (
        sa.Index("ix_wardrobe_item_user_created_at", "user_id", "created_at"),
    )

    id: so.Mapped[int] = so.mapped_column(primary_key=True, index=True)

    user_id: so.Mapped[str] = so.mapped_column(
        sa.ForeignKey("user.user_id"),
        index=True,
        nullable=False
    )

    name: so.Mapped[str] = so.mapped_column(
        sa.String(120),
        nullable=False
    )

    image_filename: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(255)
    )

    created_at: so.Mapped[datetime] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    user: so.Mapped["User"] = so.relationship(
        back_populates="wardrobe_items"
    )

    def __repr__(self) -> str:
        return f"<WardrobeItem {self.id} - {self.name} - {self.user_id}>"
