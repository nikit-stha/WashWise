from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_required

from app.extensions import app
from app.models.staff import Staff
from app.services.app_setting_service import (
    get_settings,
    toggle_deposit,
    toggle_collection,
)


@app.route("/staff/dashboard")
@login_required
def staff_dashboard():
    if not isinstance(current_user, Staff):
        flash("Access denied: Staff only.", "danger")
        return redirect(url_for("index"))

    settings = get_settings()

    return render_template(
        "staff_dashboard.html",
        title="Staff Control Panel",
        settings=settings,
    )


@app.route("/staff/profile")
@login_required
def staff_profile():
    if not isinstance(current_user, Staff):
        flash("Access denied: Staff only.", "danger")
        return redirect(url_for("index"))

    return render_template(
        "staff_profile.html",
        title="Staff Profile",
        staff=current_user,
    )


@app.route("/staff/toggle-deposit", methods=["POST"])
@login_required
def toggle_deposit_route():
    if not isinstance(current_user, Staff):
        flash("Unauthorized access.", "danger")
        return redirect(url_for("index"))

    new_status = toggle_deposit()
    flash(
        f"Deposits {'enabled' if new_status else 'disabled'} successfully.",
        "success",
    )
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/toggle-collection", methods=["POST"])
@login_required
def toggle_collection_route():
    if not isinstance(current_user, Staff):
        flash("Unauthorized access.", "danger")
        return redirect(url_for("index"))

    new_status = toggle_collection()
    flash(
        f"Collection {'enabled' if new_status else 'disabled'} successfully.",
        "success",
    )
    return redirect(url_for("staff_dashboard"))
