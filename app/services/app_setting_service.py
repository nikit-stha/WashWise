from app.extensions import db
from app.models.app_setting import AppSetting


def get_settings():
    return AppSetting.get_singleton()


def is_deposit_enabled():
    return get_settings().deposit_enabled


def is_collection_enabled():
    return get_settings().collection_enabled


def toggle_deposit():
    settings = get_settings()
    settings.deposit_enabled = not settings.deposit_enabled
    db.session.commit()
    return settings.deposit_enabled


def toggle_collection():
    settings = get_settings()
    settings.collection_enabled = not settings.collection_enabled
    db.session.commit()
    return settings.collection_enabled