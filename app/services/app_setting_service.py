from app.extensions import db
from app.models.app_setting import AppSetting
from app.utils.hostels import (
    HOSTEL_LABELS,
    normalize_hostel_code,
    normalize_hostel_codes,
    serialize_hostel_codes,
)


def get_settings():
    return AppSetting.get_singleton()


def _is_enabled_for_hostel(enabled: bool, selected_hostels: str | None, hostel_code: str) -> bool:
    if not enabled:
        return False

    selected_hostel_codes = normalize_hostel_codes(selected_hostels)
    if not selected_hostel_codes:
        return False

    return normalize_hostel_code(hostel_code) in selected_hostel_codes


def _requested_hostel_codes(hostel_codes) -> list[str]:
    if isinstance(hostel_codes, str):
        raw_codes = hostel_codes.split(",")
    else:
        raw_codes = hostel_codes or []

    return [
        normalize_hostel_code(hostel_code)
        for hostel_code in raw_codes
        if normalize_hostel_code(hostel_code)
    ]


def _validate_selected_hostels(hostel_codes):
    requested_codes = _requested_hostel_codes(hostel_codes)
    if not requested_codes:
        return None, "Please select at least one hostel."

    invalid_codes = [
        hostel_code
        for hostel_code in requested_codes
        if hostel_code not in HOSTEL_LABELS
    ]
    if invalid_codes:
        return None, "Please choose hostels from the list."

    return serialize_hostel_codes(requested_codes), None


def is_deposit_enabled():
    return get_settings().deposit_enabled


def is_deposit_enabled_for_hostel(hostel_code: str) -> bool:
    settings = get_settings()
    return _is_enabled_for_hostel(
        settings.deposit_enabled,
        settings.deposit_hostel_code,
        hostel_code,
    )


def is_collection_enabled():
    return get_settings().collection_enabled


def is_collection_enabled_for_hostel(hostel_code: str) -> bool:
    settings = get_settings()
    return _is_enabled_for_hostel(
        settings.collection_enabled,
        settings.collection_hostel_code,
        hostel_code,
    )


def toggle_deposit(hostel_codes=None):
    settings = get_settings()

    if settings.deposit_enabled:
        settings.deposit_enabled = False
        settings.deposit_hostel_code = None
        db.session.commit()
        return settings, None

    hostel_codes, error = _validate_selected_hostels(hostel_codes)
    if error:
        return settings, error

    settings.deposit_enabled = True
    settings.deposit_hostel_code = hostel_codes
    db.session.commit()
    return settings, None


def update_deposit_hostels(hostel_codes):
    settings = get_settings()

    if not settings.deposit_enabled:
        return settings, "Deposits are currently closed."

    hostel_codes, error = _validate_selected_hostels(hostel_codes)
    if error:
        return settings, error

    settings.deposit_hostel_code = hostel_codes
    db.session.commit()
    return settings, None


def toggle_collection(hostel_codes=None):
    settings = get_settings()

    if settings.collection_enabled:
        settings.collection_enabled = False
        settings.collection_hostel_code = None
        db.session.commit()
        return settings, None

    hostel_codes, error = _validate_selected_hostels(hostel_codes)
    if error:
        return settings, error

    settings.collection_enabled = True
    settings.collection_hostel_code = hostel_codes
    db.session.commit()
    return settings, None


def update_collection_hostels(hostel_codes):
    settings = get_settings()

    if not settings.collection_enabled:
        return settings, "Collection is currently closed."

    hostel_codes, error = _validate_selected_hostels(hostel_codes)
    if error:
        return settings, error

    settings.collection_hostel_code = hostel_codes
    db.session.commit()
    return settings, None
