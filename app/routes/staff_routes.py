from flask import render_template, flash, redirect, request, url_for
from flask_login import current_user, login_required

from app.extensions import app
from app.models.staff import Staff
from app.utils.hostels import (
    HOSTEL_CHOICES,
    get_hostel_labels,
    get_hostel_summary,
    normalize_hostel_codes,
)
from app.services.app_setting_service import (
    get_settings,
    toggle_deposit,
    toggle_collection,
    update_collection_hostels,
    update_deposit_hostels,
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
        hostel_choices=HOSTEL_CHOICES,
        deposit_hostel_label=get_hostel_summary(settings.deposit_hostel_code),
        deposit_hostel_full_label=get_hostel_labels(settings.deposit_hostel_code),
        deposit_hostel_codes=normalize_hostel_codes(settings.deposit_hostel_code),
        collection_hostel_label=get_hostel_summary(settings.collection_hostel_code),
        collection_hostel_full_label=get_hostel_labels(settings.collection_hostel_code),
        collection_hostel_codes=normalize_hostel_codes(settings.collection_hostel_code),
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

    settings, error = toggle_deposit(request.form.getlist("hostel_codes"))
    if error:
        flash(error, "danger")
        return redirect(url_for("staff_dashboard"))

    if settings.deposit_enabled:
        flash(
            f"Deposits enabled for {get_hostel_summary(settings.deposit_hostel_code)}.",
            "success",
        )
    else:
        flash("Deposits disabled successfully.", "success")

    return redirect(url_for("staff_dashboard"))


@app.route("/staff/update-deposit-hostels", methods=["POST"])
@login_required
def update_deposit_hostels_route():
    if not isinstance(current_user, Staff):
        flash("Unauthorized access.", "danger")
        return redirect(url_for("index"))

    settings, error = update_deposit_hostels(request.form.getlist("hostel_codes"))
    if error:
        flash(error, "danger")
        return redirect(url_for("staff_dashboard"))

    flash(
        f"Deposit hostels updated to {get_hostel_summary(settings.deposit_hostel_code)}.",
        "success",
    )
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/toggle-collection", methods=["POST"])
@login_required
def toggle_collection_route():
    if not isinstance(current_user, Staff):
        flash("Unauthorized access.", "danger")
        return redirect(url_for("index"))

    settings, error = toggle_collection(request.form.getlist("hostel_codes"))
    if error:
        flash(error, "danger")
        return redirect(url_for("staff_dashboard"))

    if settings.collection_enabled:
        flash(
            f"Collection enabled for {get_hostel_summary(settings.collection_hostel_code)}.",
            "success",
        )
    else:
        flash("Collection disabled successfully.", "success")

    return redirect(url_for("staff_dashboard"))


@app.route("/staff/update-collection-hostels", methods=["POST"])
@login_required
def update_collection_hostels_route():
    if not isinstance(current_user, Staff):
        flash("Unauthorized access.", "danger")
        return redirect(url_for("index"))

    settings, error = update_collection_hostels(request.form.getlist("hostel_codes"))
    if error:
        flash(error, "danger")
        return redirect(url_for("staff_dashboard"))

    flash(
        f"Collection hostels updated to {get_hostel_summary(settings.collection_hostel_code)}.",
        "success",
    )
    return redirect(url_for("staff_dashboard"))
