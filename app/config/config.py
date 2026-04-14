import os
from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
basedir = os.path.join(project_root, "app")

load_dotenv(os.path.join(project_root, ".env"))


class Config:
    ENV = os.environ.get("FLASK_ENV", "production")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"
    TEMPLATES_AUTO_RELOAD = DEBUG
    SEND_FILE_MAX_AGE_DEFAULT = 0 if DEBUG else 31536000

    _database_url = os.environ.get("DATABASE_URL")
    if _database_url and _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _database_url or "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {"timeout": 15}

    UPLOAD_FOLDER = os.path.join(basedir, "static", "uploads")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = (os.environ.get("MAIL_USERNAME") or "").strip() or None
    MAIL_PASSWORD = (os.environ.get("MAIL_PASSWORD") or "").replace(" ", "").strip() or None
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME

    ADMINS = [
        email.strip()
        for email in os.environ.get("ADMINS", "").split(",")
        if email.strip()
    ]

    # Password reset token expiry (in seconds)
    PASSWORD_RESET_TOKEN_EXPIRES = int(
        os.environ.get("PASSWORD_RESET_TOKEN_EXPIRES", 600)
    )

    EMAIL_VERIFICATION_OTP_EXPIRES = int(
        os.environ.get("EMAIL_VERIFICATION_OTP_EXPIRES", 600)
    )

    STAFF_REGISTRATION_KEY = os.environ.get("STAFF_REGISTRATION_KEY", "").strip()
