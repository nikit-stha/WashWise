import sqlalchemy as sa

from app.extensions import db
from app.models.qr_code import QRCode
from app.models.deposit import Deposit


def generate_qr_code(deposit_id: int):
    deposit = db.session.get(Deposit, deposit_id)
    if deposit is None:
        return None, "Deposit not found."

    if deposit.status != "Completed":
        return None, "Deposit is not ready for collection."

    existing_qr = db.session.scalar(
        sa.select(QRCode)
        .where(QRCode.deposit_id == deposit.id)
        .where(QRCode.is_used == False)
        .order_by(QRCode.id.desc())
    )

    if existing_qr and not existing_qr.is_expired():
        return existing_qr, None

    qr_code = QRCode(deposit_id=deposit_id)
    db.session.add(qr_code)
    db.session.commit()

    return qr_code, None


def verify_qr_code(token: str):
    qr_code = db.session.scalar(
        sa.select(QRCode).where(QRCode.token == token)
    )

    if qr_code is None:
        return None, "Invalid token."

    if qr_code.is_used:
        return None, "QR code already used."

    if qr_code.is_expired():
        return None, "QR code expired."

    deposit = db.session.get(Deposit, qr_code.deposit_id)
    if deposit is None:
        return None, "Associated deposit not found."

    deposit.status = "Collected"
    qr_code.is_used = True
    db.session.commit()

    return deposit, None