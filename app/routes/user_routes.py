from flask import render_template, flash, redirect, url_for, jsonify
from flask_login import current_user, login_required
from app.extensions import app
from app.models.user import User
from app.services.app_setting_service import get_settings
from app.services.deposit_service import (
    get_completed_user_deposits,
    get_recent_active_user_deposits,
)


def _get_user_dashboard_notifications(student_id):
    settings = get_settings()
    notifications = []

    if settings.deposit_enabled:
        notifications.append({
            "id": "deposit-open",
            "title": "Deposits are open",
            "message": "Staff has opened laundry deposits. You can create a new deposit now.",
            "url": url_for("create_deposit_route"),
            "tone": "info",
        })

    if settings.collection_enabled:
        notifications.append({
            "id": "collection-open",
            "title": "Collection is open",
            "message": "Staff has opened collection. Collect completed clothes from the laundry counter.",
            "url": url_for("my_deposits"),
            "tone": "success",
        })

    for deposit in get_completed_user_deposits(student_id):
        item_count = deposit.service.item_count if deposit.service else len(deposit.items)
        item_status = (
            f"Your {item_count} item is completed."
            if item_count == 1
            else f"Your {item_count} items are completed."
        )
        notifications.append({
            "id": f"deposit-completed-{deposit.id}",
            "title": "Your Deposit is ready",
            "message": (
                f"{item_status} Please come to the laundry to take your clothes."
            ),
            "url": url_for("view_deposit", deposit_id=deposit.id),
            "tone": "success",
        })

    return notifications


@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if not isinstance(current_user, User):
        flash("Access denied: Users only.")
        return redirect(url_for('index'))

    return render_template(
        'user_dashboard.html',
        title="Student Portal",
        active_deposits=get_recent_active_user_deposits(current_user.user_id),
        notifications=_get_user_dashboard_notifications(current_user.user_id),
    )


@app.route('/user/notifications')
@login_required
def user_notifications():
    if not isinstance(current_user, User):
        return jsonify({"error": "Access denied: Users only."}), 403

    notifications = _get_user_dashboard_notifications(current_user.user_id)
    return jsonify({
        "count": len(notifications),
        "notifications": notifications,
    })


@app.route('/user/profile')
@login_required
def user_profile():
    if not isinstance(current_user, User):
        flash("Access denied: Users only.")
        return redirect(url_for('index'))

    return render_template('profile.html', title="My Profile", user=current_user)
