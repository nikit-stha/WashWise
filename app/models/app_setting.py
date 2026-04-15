from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so

from app.extensions import db


_SCHEMA_COLUMNS_CHECKED = False


def _ensure_app_setting_columns():
    global _SCHEMA_COLUMNS_CHECKED

    if _SCHEMA_COLUMNS_CHECKED:
        return

    bind = db.session.get_bind()
    inspector = sa.inspect(bind)
    if AppSetting.__tablename__ not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(AppSetting.__tablename__)
    }

    optional_columns = {
        "deposit_hostel_code": "VARCHAR(255)",
        "collection_hostel_code": "VARCHAR(255)",
    }

    added_columns = False
    for column_name, column_type in optional_columns.items():
        if column_name not in existing_columns:
            db.session.execute(
                sa.text(
                    f"ALTER TABLE {AppSetting.__tablename__} "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )
            added_columns = True

    if added_columns:
        db.session.commit()

    _SCHEMA_COLUMNS_CHECKED = True


class AppSetting(db.Model):
    __tablename__ = "app_setting"

    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    deposit_enabled: so.Mapped[bool] = so.mapped_column(
        sa.Boolean,
        default=False,
        nullable=False,
    )

    collection_enabled: so.Mapped[bool] = so.mapped_column(
        sa.Boolean,
        default=False,
        nullable=False,
    )

    deposit_hostel_code: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(255),
        nullable=True,
    )

    collection_hostel_code: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(255),
        nullable=True,
    )

    updated_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def get_singleton(cls):
        _ensure_app_setting_columns()

        setting = db.session.scalar(sa.select(cls).limit(1))
        if setting is None:
            setting = cls()
            db.session.add(setting)
            db.session.commit()
        else:
            needs_commit = False

            if setting.deposit_enabled and not setting.deposit_hostel_code:
                setting.deposit_enabled = False
                needs_commit = True

            if setting.collection_enabled and not setting.collection_hostel_code:
                setting.collection_enabled = False
                needs_commit = True

            if needs_commit:
                db.session.commit()

        return setting
