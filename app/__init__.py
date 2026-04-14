import os

from flask import flash, redirect, request, url_for

from app.extensions import app, db, login_manager

from app.models.user import User
from app.models.staff import Staff
from app.models.deposit import Deposit
from app.models.clothing_item import ClothingItem
from app.models.service_detail import ServiceDetail
from app.models.qr_code import QRCode
from app.models.wardrobe_item import WardrobeItem
from app.models.app_setting import AppSetting

from app.routes import auth_routes
from app.routes import user_routes
from app.routes import staff_routes
from app.routes import deposit_routes
from app.routes import qr_routes
from app.routes import wardrobe_routes


def ensure_database_ready():
    with app.app_context():
        db.create_all()
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        AppSetting.get_singleton()


ensure_database_ready()


@app.context_processor
def inject_asset_helpers():
    def static_asset_url(filename: str) -> str:
        static_path = os.path.join(app.static_folder, filename)

        try:
            version = int(os.path.getmtime(static_path))
        except OSError:
            return url_for("static", filename=filename)

        return url_for("static", filename=filename, v=version)

    return {"static_asset_url": static_asset_url}


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, user_id)
    if user is not None:
        return user

    try:
        return db.session.get(Staff, int(user_id))
    except (ValueError, TypeError):
        return None


@login_manager.unauthorized_handler
def handle_unauthorized():
    next_path = request.full_path.rstrip("?")

    flash(
        login_manager.login_message,
        login_manager.login_message_category,
    )

    if request.path.startswith("/staff"):
        return redirect(url_for("staff_login", next=next_path))

    return redirect(url_for("user_login", next=next_path))
