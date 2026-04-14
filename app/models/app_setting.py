from __future__ import annotations

from datetime import datetime, timezone
import sqlalchemy as sa
import sqlalchemy.orm as so

from app.extensions import db


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

    updated_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def get_singleton(cls):
        setting = db.session.scalar(sa.select(cls).limit(1))
        if setting is None:
            setting = cls()
            db.session.add(setting)
            db.session.commit()
        return setting