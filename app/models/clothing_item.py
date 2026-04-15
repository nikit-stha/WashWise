from __future__ import annotations

import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import Optional

from app.extensions import db


_SCHEMA_COLUMNS_CHECKED = False


def _ensure_clothing_item_columns():
    global _SCHEMA_COLUMNS_CHECKED

    if _SCHEMA_COLUMNS_CHECKED:
        return

    bind = db.session.get_bind()
    inspector = sa.inspect(bind)
    if ClothingItem.__tablename__ not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(ClothingItem.__tablename__)
    }

    optional_columns = {
        "clothing_type": "VARCHAR(80)",
    }

    added_columns = False
    for column_name, column_type in optional_columns.items():
        if column_name not in existing_columns:
            db.session.execute(
                sa.text(
                    f"ALTER TABLE {ClothingItem.__tablename__} "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )
            added_columns = True

    if added_columns:
        db.session.commit()

    _SCHEMA_COLUMNS_CHECKED = True


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

    clothing_type: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(80),
        nullable=True,
    )

    deposit: so.Mapped["Deposit"] = so.relationship(
        back_populates="items"
    )

    @classmethod
    def ensure_schema(cls):
        _ensure_clothing_item_columns()
