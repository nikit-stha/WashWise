from collections import Counter

from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
import sqlalchemy as sa

from app.extensions import app, db
from app.models.user import User
from app.models.staff import Staff
from app.models.deposit import Deposit
from app.models.wardrobe_item import WardrobeItem
from app.services.deposit_service import (
    create_deposit,
    delete_user_deposit_if_allowed,
    get_active_user_deposit,
    get_user_deposits,
    get_all_deposits,
    get_deposit_for_view,
    update_deposit_items_from_wardrobe,
    assign_staff_to_deposit,
    update_deposit_status,
)
from app.services.app_setting_service import (
    get_settings,
    is_deposit_enabled,
    is_collection_enabled,
)


@app.route("/deposit/create", methods=["GET", "POST"])
@login_required
def create_deposit_route():
    if not isinstance(current_user, User):
        flash("Access denied: Users only.", "danger")
        return redirect(url_for("index"))

    if not is_deposit_enabled():
        flash(
            "Deposits are currently closed. Please wait for staff to enable them.",
            "warning",
        )
        return redirect(url_for("my_deposits"))

    active_deposit = get_active_user_deposit(current_user.user_id)
    if active_deposit is not None:
        flash(
            "You already have an active deposit. "
            "You can create another deposit after it is collected.",
            "warning",
        )
        return redirect(url_for("view_deposit", deposit_id=active_deposit.id))

    wardrobe_items = db.session.scalars(
        sa.select(WardrobeItem)
        .options(
            sa.orm.load_only(
                WardrobeItem.id,
                WardrobeItem.name,
                WardrobeItem.image_filename,
                WardrobeItem.created_at,
            )
        )
        .where(WardrobeItem.user_id == current_user.user_id)
        .order_by(WardrobeItem.created_at.desc())
    ).all()

    settings = get_settings()

    if request.method == "POST":
        wardrobe_item_ids = request.form.getlist("wardrobe_item_ids", type=int)

        if not wardrobe_item_ids:
            flash("Please select at least one clothing item from your wardrobe.", "danger")
            return redirect(url_for("create_deposit_route"))

        if len(wardrobe_item_ids) > 10:
            flash("Maximum 10 wardrobe items allowed per deposit.", "danger")
            return redirect(url_for("create_deposit_route"))

        deposit, error = create_deposit(
            student_id=current_user.user_id,
            descriptions=[],
            image_filenames=[],
            wardrobe_item_ids=wardrobe_item_ids,
        )

        if error:
            flash(error, "danger")
            return redirect(url_for("create_deposit_route"))

        flash("Deposit created successfully.", "success")
        return redirect(url_for("view_deposit", deposit_id=deposit.id))

    return render_template(
        "create_deposit.html",
        title="Create Deposit",
        wardrobe_items=wardrobe_items,
        settings=settings,
    )


@app.route("/deposit/<int:deposit_id>")
@login_required
def view_deposit(deposit_id):
    deposit = get_deposit_for_view(deposit_id)

    if deposit is None:
        flash("Deposit not found.", "danger")
        return redirect(url_for("index"))

    if isinstance(current_user, User) and deposit.student_id != current_user.user_id:
        flash("Access denied.", "danger")
        return redirect(url_for("index"))

    settings = get_settings()

    return render_template(
        "deposit_detail.html",
        title="Deposit Details",
        deposit=deposit,
        settings=settings,
    )


@app.route("/deposit/<int:deposit_id>/edit", methods=["GET", "POST"])
@login_required
def edit_deposit_route(deposit_id):
    if not isinstance(current_user, User):
        flash("Access denied: Users only.", "danger")
        return redirect(url_for("index"))

    deposit = get_deposit_for_view(deposit_id)

    if deposit is None:
        flash("Deposit not found.", "danger")
        return redirect(url_for("my_deposits"))

    if deposit.student_id != current_user.user_id:
        flash("Access denied.", "danger")
        return redirect(url_for("my_deposits"))

    if deposit.status != "Not Given":
        flash("This deposit is already in progress and can no longer be edited.", "warning")
        return redirect(url_for("view_deposit", deposit_id=deposit.id))

    wardrobe_items = db.session.scalars(
        sa.select(WardrobeItem)
        .options(
            sa.orm.load_only(
                WardrobeItem.id,
                WardrobeItem.name,
                WardrobeItem.image_filename,
                WardrobeItem.created_at,
            )
        )
        .where(WardrobeItem.user_id == current_user.user_id)
        .order_by(WardrobeItem.created_at.desc())
    ).all()

    selected_item_ids = set()
    remaining_item_names = Counter(item.description for item in deposit.items)
    for wardrobe_item in wardrobe_items:
        if remaining_item_names[wardrobe_item.name] > 0:
            selected_item_ids.add(wardrobe_item.id)
            remaining_item_names[wardrobe_item.name] -= 1

    if request.method == "POST":
        wardrobe_item_ids = request.form.getlist("wardrobe_item_ids", type=int)

        deposit, error = update_deposit_items_from_wardrobe(
            deposit_id=deposit_id,
            student_id=current_user.user_id,
            wardrobe_item_ids=wardrobe_item_ids,
        )

        if error:
            flash(error, "danger")
            selected_item_ids = set(wardrobe_item_ids)
        elif deposit is None:
            flash("Deposit removed successfully.", "success")
            return redirect(url_for("my_deposits"))
        else:
            flash("Deposit clothes updated successfully.", "success")
            return redirect(url_for("view_deposit", deposit_id=deposit.id))

    return render_template(
        "edit_deposit.html",
        title="Edit Deposit",
        deposit=deposit,
        wardrobe_items=wardrobe_items,
        selected_item_ids=selected_item_ids,
    )


@app.route("/deposit/<int:deposit_id>/delete", methods=["POST"])
@login_required
def delete_deposit_route(deposit_id):
    if not isinstance(current_user, User):
        flash("Access denied: Users only.", "danger")
        return redirect(url_for("index"))

    deleted, error = delete_user_deposit_if_allowed(
        deposit_id=deposit_id,
        student_id=current_user.user_id,
    )

    if error:
        flash(error, "danger")
        return redirect(url_for("view_deposit", deposit_id=deposit_id))

    if deleted:
        flash("Deposit removed successfully.", "success")

    return redirect(url_for("my_deposits"))


@app.route("/user/deposits")
@login_required
def my_deposits():
    if not isinstance(current_user, User):
        flash("Access denied: Users only.", "danger")
        return redirect(url_for("index"))

    deposits = get_user_deposits(current_user.user_id)
    settings = get_settings()

    return render_template(
        "my_deposits.html",
        title="My Deposits",
        deposits=deposits,
        settings=settings,
    )


@app.route("/staff/deposits")
@login_required
def staff_deposits():
    if not isinstance(current_user, Staff):
        flash("Access denied: Staff only.", "danger")
        return redirect(url_for("index"))

    deposits = get_all_deposits()
    settings = get_settings()

    return render_template(
        "staff_deposits.html",
        title="All Deposits",
        deposits=deposits,
        settings=settings,
    )


@app.route("/deposit/<int:deposit_id>/assign", methods=["POST"])
@login_required
def assign_deposit(deposit_id):
    if not isinstance(current_user, Staff):
        flash("Access denied: Staff only.", "danger")
        return redirect(url_for("index"))

    deposit, error = assign_staff_to_deposit(deposit_id, current_user.id)

    if error:
        flash(error, "danger")
        return redirect(url_for("staff_deposits"))

    flash("Deposit assigned successfully.", "success")
    return redirect(url_for("view_deposit", deposit_id=deposit.id))


@app.route("/deposit/<int:deposit_id>/status", methods=["POST"])
@login_required
def update_deposit_status_route(deposit_id):
    if not isinstance(current_user, Staff):
        flash("Access denied: Staff only.", "danger")
        return redirect(url_for("index"))

    new_status = request.form.get("status", "").strip()

    deposit, error = update_deposit_status(deposit_id, new_status)

    if error:
        flash(error, "danger")
        return redirect(url_for("staff_deposits"))

    flash("Deposit status updated.", "success")
    return redirect(url_for("view_deposit", deposit_id=deposit.id))


@app.route("/deposit/<int:deposit_id>/collect", methods=["POST"])
@login_required
def collect_deposit_route(deposit_id):
    if not isinstance(current_user, User):
        flash("Access denied: Users only.", "danger")
        return redirect(url_for("index"))

    if not is_collection_enabled():
        flash(
            "Collection is currently closed. Please wait for staff to enable it.",
            "warning",
        )
        return redirect(url_for("my_deposits"))

    deposit = db.session.get(Deposit, deposit_id)

    if deposit is None:
        flash("Deposit not found.", "danger")
        return redirect(url_for("my_deposits"))

    if deposit.student_id != current_user.user_id:
        flash("Access denied.", "danger")
        return redirect(url_for("my_deposits"))

    if not deposit.status or deposit.status.lower() != "completed":
        flash("Clothes are not ready for collection yet.", "warning")
        return redirect(url_for("my_deposits"))

    flash(
        "Collection request allowed. Continue with your collection workflow.",
        "success",
    )
    return redirect(url_for("view_deposit", deposit_id=deposit.id))
