from flask import jsonify
from flask_login import login_required, current_user

from app.extensions import app
from app.models.staff import Staff
from app.models.user import User
from app.models.deposit import Deposit
from app.services.qr_service import generate_qr_code, verify_qr_code


@app.route("/qr/generate/<int:deposit_id>", methods=["POST"])
@login_required
def generate_qr(deposit_id):
    deposit = Deposit.query.get(deposit_id)

    if deposit is None:
        return jsonify({"error": "Deposit not found"}), 404

    if isinstance(current_user, User):
        if deposit.student_id != current_user.user_id:
            return jsonify({"error": "Access denied"}), 403
    elif not isinstance(current_user, Staff):
        return jsonify({"error": "Access denied"}), 403

    qr_code, error = generate_qr_code(deposit_id)

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "QR generated successfully",
        "deposit_id": deposit_id,
        "token": qr_code.token,
        "expires_at": qr_code.expires_at.isoformat(),
        "is_used": qr_code.is_used
    }), 201


@app.route("/qr/scan/<string:token>", methods=["GET"])
@login_required
def scan_qr(token):
    if not isinstance(current_user, Staff):
        return jsonify({"error": "Access denied: Staff only"}), 403

    deposit, error = verify_qr_code(token)

    if error:
        return jsonify({"error": error}), 400

    if deposit.staff_id is None:
        deposit.staff_id = current_user.id
        from app.extensions import db
        db.session.commit()

    return jsonify({
        "message": "QR code valid",
        "deposit": {
            "id": deposit.id,
            "student_id": deposit.student_id,
            "staff_id": deposit.staff_id,
            "status": deposit.status,
            "created_at": deposit.created_at.isoformat()
        }
    }), 200