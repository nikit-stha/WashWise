from flask import Flask, flash, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from werkzeug.exceptions import RequestEntityTooLarge

import logging
from logging.handlers import SMTPHandler

from app.config.config import Config


app = Flask(__name__)
app.config.from_object(Config)

# -----------------------------
# Extensions
# -----------------------------
db = SQLAlchemy(app, session_options={"expire_on_commit": False})
migrate = Migrate(app, db)
mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_view = "user_login"
login_manager.login_message = "Please log in to access this page."


# -----------------------------
# Email Error Logging (Production)
# -----------------------------
if (
    not app.debug
    and app.config.get("MAIL_SERVER")
    and app.config.get("MAIL_DEFAULT_SENDER")
    and app.config.get("ADMINS")
):
    auth = None
    if app.config["MAIL_USERNAME"] or app.config["MAIL_PASSWORD"]:
        auth = (app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])

    secure = None
    if app.config["MAIL_USE_TLS"]:
        secure = ()

    mail_handler = SMTPHandler(
        mailhost=(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]),
        fromaddr=app.config["MAIL_DEFAULT_SENDER"],
        toaddrs=app.config["ADMINS"],
        subject="WashWise Application Error",
        credentials=auth,
        secure=secure,
    )

    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(error):
    flash("Uploaded file is too large. Please choose an image smaller than 20 MB.", "danger")

    if request.referrer:
        return redirect(request.referrer)

    return redirect(url_for("index"))
