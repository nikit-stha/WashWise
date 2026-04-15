import secrets
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import sqlalchemy as sa
from flask import current_app, session
from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.user import User
from app.models.staff import Staff
from app.utils.validators import (
    is_valid_email,
    is_valid_password,
    is_thapar_email,
)
from app.utils.hostels import is_valid_hostel_code, normalize_hostel_code


PENDING_USER_REGISTRATION_SESSION_KEY = "pending_user_registration"
PENDING_STAFF_REGISTRATION_SESSION_KEY = "pending_staff_registration"
USER_VERIFICATION_ATTEMPTS_SESSION_KEY = "user_email_verification_attempts"
STAFF_VERIFICATION_ATTEMPTS_SESSION_KEY = "staff_email_verification_attempts"
EMAIL_VERIFICATION_MAX_ATTEMPTS = 5


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _store_pending_registration(session_key: str, payload: dict):
    session[session_key] = payload
    session.modified = True


def _get_pending_registration(session_key: str, email: str | None = None):
    pending = session.get(session_key)
    if not pending:
        return None

    pending_email = (pending.get("email") or "").strip().lower()
    if email is not None and pending_email != (email or "").strip().lower():
        return None

    return pending


def _clear_pending_registration(session_key: str):
    session.pop(session_key, None)
    session.modified = True


def _set_verification_attempts(session_key: str, email: str, attempts_remaining: int):
    email = (email or "").strip().lower()
    attempts_map = dict(session.get(session_key, {}))
    attempts_map[email] = attempts_remaining
    session[session_key] = attempts_map
    session.modified = True


def _get_verification_attempts(session_key: str, email: str) -> int:
    email = (email or "").strip().lower()
    attempts_map = session.get(session_key, {})
    return int(attempts_map.get(email, EMAIL_VERIFICATION_MAX_ATTEMPTS))


def _clear_verification_attempts(session_key: str, email: str):
    email = (email or "").strip().lower()
    attempts_map = dict(session.get(session_key, {}))
    if email in attempts_map:
        attempts_map.pop(email, None)
        session[session_key] = attempts_map
        session.modified = True


def _decrement_verification_attempts(session_key: str, email: str) -> int:
    remaining = max(_get_verification_attempts(session_key, email) - 1, 0)
    _set_verification_attempts(session_key, email, remaining)
    return remaining


def _pending_attempts_remaining(pending: dict) -> int:
    return int(pending.get("otp_attempts_remaining", EMAIL_VERIFICATION_MAX_ATTEMPTS))


def _pending_registration_has_valid_otp(pending: dict, otp: str) -> bool:
    otp_hash = pending.get("otp_hash")
    expires_at = _parse_utc_datetime(pending.get("otp_expires_at"))

    if not otp_hash or expires_at is None or _utc_now() > expires_at:
        return False

    return check_password_hash(otp_hash, otp)


def _set_pending_registration_attempts(pending: dict, attempts_remaining: int):
    pending["otp_attempts_remaining"] = attempts_remaining


def _decrement_pending_registration_attempts(session_key: str, pending: dict) -> int:
    remaining = max(_pending_attempts_remaining(pending) - 1, 0)
    _set_pending_registration_attempts(pending, remaining)
    if remaining == 0:
        pending["otp_hash"] = None
        pending["otp_expires_at"] = None
    _store_pending_registration(session_key, pending)
    return remaining


def _pending_registration_matches_password(pending: dict | None, password: str) -> bool:
    if pending is None:
        return False

    password_hash = pending.get("password_hash")
    if not password_hash:
        return False

    return check_password_hash(password_hash, password or "")


def _pending_user_recipient(pending: dict):
    return SimpleNamespace(
        email=pending["email"],
        name=pending.get("name") or pending.get("username"),
    )


def _pending_staff_recipient(pending: dict):
    return SimpleNamespace(
        email=pending["email"],
        name=pending["name"],
    )


def normalize_hostel_number(hostel_number: str) -> str:
    return normalize_hostel_code(hostel_number)


def generate_user_id(hostel_number: str) -> str:
    prefix = normalize_hostel_number(hostel_number)

    latest_user_id = db.session.scalar(
        sa.select(User.user_id)
        .where(User.user_id.like(f"{prefix}-%"))
        .order_by(User.user_id.desc())
        .limit(1)
    )

    max_number = 0
    if latest_user_id:
        try:
            max_number = int(latest_user_id.split("-")[1])
        except (IndexError, ValueError):
            max_number = 0

    return f"{prefix}-{max_number + 1:04d}"


def register_user(name, email, password, hostel_number):
    name = (name or "").strip()
    email = (email or "").strip().lower()
    hostel_number = normalize_hostel_number(hostel_number)
    password = password or ""

    if not name:
        return None, None, "Name is required."

    if not hostel_number:
        return None, None, "Please select your hostel."

    if not is_valid_hostel_code(hostel_number):
        return None, None, "Please choose a hostel from the list."

    if not is_valid_email(email):
        return None, None, "Invalid email format."

    if not is_thapar_email(email):
        return None, None, "Only @thapar.edu email addresses are allowed for students."

    if not is_valid_password(password):
        return None, None, (
            "Password must be more than 6 characters and contain "
            "a special character."
        )

    existing_email = db.session.scalar(
        sa.select(User).where(User.email == email)
    )
    if existing_email:
        return None, None, "Email already registered."

    otp = _generate_otp()
    expires_at = _utc_now() + timedelta(
        seconds=current_app.config["EMAIL_VERIFICATION_OTP_EXPIRES"]
    )

    _store_pending_registration(
        PENDING_USER_REGISTRATION_SESSION_KEY,
        {
            "name": name,
            "email": email,
            "hostel_number": hostel_number,
            "password_hash": generate_password_hash(password),
            "otp_hash": generate_password_hash(otp),
            "otp_expires_at": expires_at.isoformat(),
            "otp_attempts_remaining": EMAIL_VERIFICATION_MAX_ATTEMPTS,
        },
    )

    return SimpleNamespace(email=email, name=name), otp, None


def complete_user_registration(email: str, otp: str):
    pending = _get_pending_registration(
        PENDING_USER_REGISTRATION_SESSION_KEY,
        email=email,
    )
    if pending is None:
        return None, "No pending registration found. Please register again."

    if not _pending_registration_has_valid_otp(pending, otp.strip()):
        remaining = _decrement_pending_registration_attempts(
            PENDING_USER_REGISTRATION_SESSION_KEY,
            pending,
        )
        if remaining == 0:
            return None, "OTP attempt limit reached. Please request a new OTP."
        return None, f"Invalid or expired OTP. {remaining} attempt(s) remaining."

    name = (pending.get("name") or pending.get("username") or "").strip()
    email = (pending.get("email") or "").strip().lower()
    hostel_number = normalize_hostel_number(pending.get("hostel_number"))
    password_hash = pending.get("password_hash")

    if (
        not name
        or not email
        or not hostel_number
        or not is_valid_hostel_code(hostel_number)
        or not password_hash
    ):
        _clear_pending_registration(PENDING_USER_REGISTRATION_SESSION_KEY)
        return None, "Registration data is invalid. Please register again."

    existing_email = db.session.scalar(
        sa.select(User).where(User.email == email)
    )
    if existing_email is not None:
        _clear_pending_registration(PENDING_USER_REGISTRATION_SESSION_KEY)
        return None, "Email already registered. Please sign in instead."

    new_user = User(
        user_id=generate_user_id(hostel_number),
        name=name,
        email=email,
        hostel_number=hostel_number,
        password_hash=password_hash,
        is_email_verified=True,
        email_verification_otp_hash=None,
        email_verification_otp_expires_at=None,
    )

    db.session.add(new_user)
    db.session.commit()
    _clear_pending_registration(PENDING_USER_REGISTRATION_SESSION_KEY)

    return new_user, None


def resend_pending_user_registration_otp(email: str):
    pending = _get_pending_registration(
        PENDING_USER_REGISTRATION_SESSION_KEY,
        email=email,
    )
    if pending is None:
        return None, None, "No pending registration found. Please register again."

    otp = _generate_otp()
    pending["otp_hash"] = generate_password_hash(otp)
    pending["otp_expires_at"] = (
        _utc_now()
        + timedelta(seconds=current_app.config["EMAIL_VERIFICATION_OTP_EXPIRES"])
    ).isoformat()
    pending["otp_attempts_remaining"] = EMAIL_VERIFICATION_MAX_ATTEMPTS
    _store_pending_registration(PENDING_USER_REGISTRATION_SESSION_KEY, pending)

    return _pending_user_recipient(pending), otp, None


def has_pending_user_registration(email: str):
    return _get_pending_registration(
        PENDING_USER_REGISTRATION_SESSION_KEY,
        email=email,
    ) is not None


def pending_user_registration_requires_verification(email: str, password: str):
    pending = _get_pending_registration(
        PENDING_USER_REGISTRATION_SESSION_KEY,
        email=email,
    )
    return _pending_registration_matches_password(pending, password)


def login_user_service(email, password, remember=False):
    email = (email or "").strip().lower()
    password = password or ""

    if not is_valid_email(email):
        return None, None, "Invalid email format."

    if not is_thapar_email(email):
        return None, None, "Only @thapar.edu email addresses are allowed."

    user = db.session.scalar(
        sa.select(User).where(User.email == email)
    )

    if user is None or not user.check_password(password):
        return None, None, "Invalid email or password."

    if not user.is_email_verified:
        return user, "verification_required", None

    login_user(user, remember=remember)
    return user, None, None


def logout_user_service():
    logout_user()


def get_user_by_email(email: str):
    email = (email or "").strip().lower()
    if not email:
        return None
    return db.session.scalar(
        sa.select(User).where(User.email == email)
    )


def get_user_from_reset_token(token: str):
    return User.verify_reset_password_token(token)


def reset_user_password(token: str, new_password: str):
    user = User.verify_reset_password_token(token)
    if user is None:
        return None, "Invalid or expired password reset link."

    if not is_valid_password(new_password):
        return None, (
            "Password must be more than 6 characters and contain "
            "a special character."
        )

    user.set_password(new_password)
    db.session.commit()

    return user, None


def issue_user_email_verification_otp(email: str):
    user = get_user_by_email(email)
    if user is None:
        return None, None, "User not found."

    if user.is_email_verified:
        return user, None, "Email is already verified."

    otp = user.generate_email_verification_otp()
    db.session.commit()
    _set_verification_attempts(
        USER_VERIFICATION_ATTEMPTS_SESSION_KEY,
        user.email,
        EMAIL_VERIFICATION_MAX_ATTEMPTS,
    )
    return user, otp, None


def verify_user_email_otp(email: str, otp: str):
    user = get_user_by_email(email)
    if user is None:
        return None, "User not found."

    if user.is_email_verified:
        _clear_verification_attempts(USER_VERIFICATION_ATTEMPTS_SESSION_KEY, email)
        return user, None

    if not user.verify_email_otp(otp.strip()):
        remaining = _decrement_verification_attempts(
            USER_VERIFICATION_ATTEMPTS_SESSION_KEY,
            user.email,
        )
        if remaining == 0:
            user.email_verification_otp_hash = None
            user.email_verification_otp_expires_at = None
            db.session.commit()
            return None, "OTP attempt limit reached. Please request a new OTP."
        return None, f"Invalid or expired OTP. {remaining} attempt(s) remaining."

    user.mark_email_verified()
    db.session.commit()
    _clear_verification_attempts(USER_VERIFICATION_ATTEMPTS_SESSION_KEY, user.email)
    return user, None


def register_staff(name, email, password, registration_key):
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    registration_key = (registration_key or "").strip()

    if not name:
        return None, None, "Name is required."

    if not is_valid_email(email):
        return None, None, "Invalid email format."

    if not is_valid_password(password):
        return None, None, (
            "Password must be more than 6 characters and contain "
            "a special character."
        )

    expected_key = current_app.config.get("STAFF_REGISTRATION_KEY", "").strip()
    if not expected_key:
        return None, None, "Staff registration is currently unavailable."

    if registration_key != expected_key:
        return None, None, "Invalid staff registration key."

    existing_staff = db.session.scalar(
        sa.select(Staff).where(Staff.email == email)
    )
    if existing_staff:
        return None, None, "Email already registered."

    otp = _generate_otp()
    expires_at = _utc_now() + timedelta(
        seconds=current_app.config["EMAIL_VERIFICATION_OTP_EXPIRES"]
    )

    _store_pending_registration(
        PENDING_STAFF_REGISTRATION_SESSION_KEY,
        {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "otp_hash": generate_password_hash(otp),
            "otp_expires_at": expires_at.isoformat(),
            "otp_attempts_remaining": EMAIL_VERIFICATION_MAX_ATTEMPTS,
        },
    )

    return SimpleNamespace(email=email, name=name), otp, None


def complete_staff_registration(email: str, otp: str):
    pending = _get_pending_registration(
        PENDING_STAFF_REGISTRATION_SESSION_KEY,
        email=email,
    )
    if pending is None:
        return None, "No pending staff registration found. Please register again."

    if not _pending_registration_has_valid_otp(pending, otp.strip()):
        remaining = _decrement_pending_registration_attempts(
            PENDING_STAFF_REGISTRATION_SESSION_KEY,
            pending,
        )
        if remaining == 0:
            return None, "OTP attempt limit reached. Please request a new OTP."
        return None, f"Invalid or expired OTP. {remaining} attempt(s) remaining."

    name = (pending.get("name") or "").strip()
    email = (pending.get("email") or "").strip().lower()
    password_hash = pending.get("password_hash")

    if not name or not email or not password_hash:
        _clear_pending_registration(PENDING_STAFF_REGISTRATION_SESSION_KEY)
        return None, "Registration data is invalid. Please register again."

    existing_staff = db.session.scalar(
        sa.select(Staff).where(Staff.email == email)
    )
    if existing_staff is not None:
        _clear_pending_registration(PENDING_STAFF_REGISTRATION_SESSION_KEY)
        return None, "Email already registered. Please sign in instead."

    new_staff = Staff(
        name=name,
        email=email,
        password_hash=password_hash,
        is_email_verified=True,
        email_verification_otp_hash=None,
        email_verification_otp_expires_at=None,
    )

    db.session.add(new_staff)
    db.session.commit()
    _clear_pending_registration(PENDING_STAFF_REGISTRATION_SESSION_KEY)

    return new_staff, None


def resend_pending_staff_registration_otp(email: str):
    pending = _get_pending_registration(
        PENDING_STAFF_REGISTRATION_SESSION_KEY,
        email=email,
    )
    if pending is None:
        return None, None, "No pending staff registration found. Please register again."

    otp = _generate_otp()
    pending["otp_hash"] = generate_password_hash(otp)
    pending["otp_expires_at"] = (
        _utc_now()
        + timedelta(seconds=current_app.config["EMAIL_VERIFICATION_OTP_EXPIRES"])
    ).isoformat()
    pending["otp_attempts_remaining"] = EMAIL_VERIFICATION_MAX_ATTEMPTS
    _store_pending_registration(PENDING_STAFF_REGISTRATION_SESSION_KEY, pending)

    return _pending_staff_recipient(pending), otp, None


def has_pending_staff_registration(email: str):
    return _get_pending_registration(
        PENDING_STAFF_REGISTRATION_SESSION_KEY,
        email=email,
    ) is not None


def pending_staff_registration_requires_verification(email: str, password: str):
    pending = _get_pending_registration(
        PENDING_STAFF_REGISTRATION_SESSION_KEY,
        email=email,
    )
    return _pending_registration_matches_password(pending, password)


def login_staff_service(email, password, registration_key, remember=False):
    email = (email or "").strip().lower()
    password = password or ""
    registration_key = (registration_key or "").strip()

    if not is_valid_email(email):
        return None, None, "Invalid email format."

    expected_key = current_app.config.get("STAFF_REGISTRATION_KEY", "").strip()
    if not expected_key:
        return None, None, "Staff login is currently unavailable."

    if registration_key != expected_key:
        return None, None, "Invalid staff registration key."

    staff = db.session.scalar(
        sa.select(Staff).where(Staff.email == email)
    )

    if staff is None or not staff.check_password(password):
        return None, None, "Invalid email or password."

    if not staff.is_email_verified:
        return staff, "verification_required", None

    login_user(staff, remember=remember)
    return staff, None, None


def get_staff_by_email(email: str):
    email = (email or "").strip().lower()
    if not email:
        return None
    return db.session.scalar(
        sa.select(Staff).where(Staff.email == email)
    )


def get_staff_from_reset_token(token: str):
    return Staff.verify_reset_password_token(token)


def reset_staff_password(token: str, new_password: str):
    staff = Staff.verify_reset_password_token(token)
    if staff is None:
        return None, "Invalid or expired password reset link."

    if not is_valid_password(new_password):
        return None, (
            "Password must be more than 6 characters and contain "
            "a special character."
        )

    staff.set_password(new_password)
    db.session.commit()

    return staff, None


def issue_staff_email_verification_otp(email: str):
    staff = get_staff_by_email(email)
    if staff is None:
        return None, None, "Staff account not found."

    if staff.is_email_verified:
        return staff, None, "Email is already verified."

    otp = staff.generate_email_verification_otp()
    db.session.commit()
    _set_verification_attempts(
        STAFF_VERIFICATION_ATTEMPTS_SESSION_KEY,
        staff.email,
        EMAIL_VERIFICATION_MAX_ATTEMPTS,
    )
    return staff, otp, None


def verify_staff_email_otp(email: str, otp: str):
    staff = get_staff_by_email(email)
    if staff is None:
        return None, "Staff account not found."

    if staff.is_email_verified:
        _clear_verification_attempts(STAFF_VERIFICATION_ATTEMPTS_SESSION_KEY, email)
        return staff, None

    if not staff.verify_email_otp(otp.strip()):
        remaining = _decrement_verification_attempts(
            STAFF_VERIFICATION_ATTEMPTS_SESSION_KEY,
            staff.email,
        )
        if remaining == 0:
            staff.email_verification_otp_hash = None
            staff.email_verification_otp_expires_at = None
            db.session.commit()
            return None, "OTP attempt limit reached. Please request a new OTP."
        return None, f"Invalid or expired OTP. {remaining} attempt(s) remaining."

    staff.mark_email_verified()
    db.session.commit()
    _clear_verification_attempts(STAFF_VERIFICATION_ATTEMPTS_SESSION_KEY, staff.email)
    return staff, None
