from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.orm as so

from app.extensions import db


_SCHEMA_COLUMNS_CHECKED = False


def _ensure_wardrobe_item_columns():
    global _SCHEMA_COLUMNS_CHECKED

    if _SCHEMA_COLUMNS_CHECKED:
        return

    bind = db.session.get_bind()
    inspector = sa.inspect(bind)
    if WardrobeItem.__tablename__ not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(WardrobeItem.__tablename__)
    }

    optional_columns = {
        "clothing_type": "VARCHAR(80)",
    }

    added_columns = False
    for column_name, column_type in optional_columns.items():
        if column_name not in existing_columns:
            db.session.execute(
                sa.text(
                    f"ALTER TABLE {WardrobeItem.__tablename__} "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )
            added_columns = True

    if added_columns:
        db.session.commit()

    _SCHEMA_COLUMNS_CHECKED = True


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

    clothing_type: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(80),
        nullable=True,
    )

    created_at: so.Mapped[datetime] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    user: so.Mapped["User"] = so.relationship(
        back_populates="wardrobe_items"
    )

    @classmethod
    def ensure_schema(cls):
        _ensure_wardrobe_item_columns()

    def __repr__(self) -> str:
        return f"<WardrobeItem {self.id} - {self.name} - {self.user_id}>"
