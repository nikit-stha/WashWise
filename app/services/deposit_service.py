from datetime import datetime, timedelta, timezone
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.orm as so

from app.extensions import db
from app.models.deposit import Deposit
from app.models.clothing_item import ClothingItem
from app.models.service_detail import ServiceDetail
from app.models.staff import Staff
from app.models.wardrobe_item import WardrobeItem
from app.utils.file_utils import duplicate_stored_image, delete_image_if_unused


ALLOWED_STATUSES = {"Not Given", "Processing", "Completed", "Collected"}
ACTIVE_DEPOSIT_STATUSES = {"Not Given", "Processing", "Completed"}


def _start_of_week_utc(value: datetime) -> datetime:
    return value - timedelta(
        days=value.weekday(),
        hours=value.hour,
        minutes=value.minute,
        seconds=value.second,
        microseconds=value.microsecond,
    )


def create_deposit(
    student_id: str,
    descriptions: list[str],
    image_filenames: Optional[list[Optional[str]]] = None,
    wardrobe_item_ids: Optional[list[int]] = None
):
    active_deposit = get_active_user_deposit(student_id)
    if active_deposit is not None:
        return None, (
            "You already have an active deposit. "
            "You can create another deposit after it is collected."
        )

    cleaned_descriptions = [d.strip() for d in descriptions if d and d.strip()]
    image_filenames = image_filenames or []
    wardrobe_item_ids = wardrobe_item_ids or []

    selected_wardrobe_items = []
    if wardrobe_item_ids:
        selected_wardrobe_items = db.session.scalars(
            sa.select(WardrobeItem)
            .options(
                so.load_only(
                    WardrobeItem.id,
                    WardrobeItem.name,
                    WardrobeItem.image_filename,
                )
            )
            .where(
                WardrobeItem.user_id == student_id,
                WardrobeItem.id.in_(wardrobe_item_ids)
            )
        ).all()

    total_items_selected = len(cleaned_descriptions) + len(selected_wardrobe_items)

    if total_items_selected == 0:
        return None, "At least one clothing item is required."

    if total_items_selected > 10:
        return None, "Maximum 10 clothing items per deposit."

    now = datetime.now(timezone.utc)
    week_start = _start_of_week_utc(now)
    week_end = week_start + timedelta(days=7)

    weekly_count = db.session.scalar(
        sa.select(sa.func.count())
        .select_from(Deposit)
        .where(
            Deposit.student_id == student_id,
            Deposit.created_at >= week_start,
            Deposit.created_at < week_end,
        )
    ) or 0

    if weekly_count >= 2:
        return None, "You have already made 2 deposits this week."

    deposit = Deposit(
        student_id=student_id,
        status="Not Given"
    )

    for i, desc in enumerate(cleaned_descriptions):
        image_filename = image_filenames[i] if i < len(image_filenames) else None
        item = ClothingItem(
            description=desc,
            image_filename=image_filename
        )
        deposit.items.append(item)

    for wardrobe_item in selected_wardrobe_items:
        archived_image_filename = None
        if wardrobe_item.image_filename:
            archived_image_filename = duplicate_stored_image(
                wardrobe_item.image_filename,
                folder_name=f"{student_id}_deposits",
            )

        item = ClothingItem(
            description=wardrobe_item.name,
            image_filename=archived_image_filename or wardrobe_item.image_filename
        )
        deposit.items.append(item)

    total_items = len(deposit.items)

    deposit.service = ServiceDetail(
        item_count=total_items
    )

    db.session.add(deposit)
    db.session.commit()

    return deposit, None


def get_user_deposits(student_id: str):
    deposits = db.session.scalars(
        sa.select(Deposit)
        .options(
            so.load_only(
                Deposit.id,
                Deposit.status,
                Deposit.created_at,
            )
        )
        .where(Deposit.student_id == student_id)
        .order_by(Deposit.created_at.desc())
    ).all()
    return deposits


def get_recent_active_user_deposits(student_id: str, limit: int = 5):
    deposits = db.session.scalars(
        sa.select(Deposit)
        .options(
            so.load_only(
                Deposit.id,
                Deposit.status,
                Deposit.created_at,
            ),
            so.selectinload(Deposit.service).load_only(ServiceDetail.item_count),
            so.selectinload(Deposit.items).load_only(ClothingItem.id),
        )
        .where(
            Deposit.student_id == student_id,
            Deposit.status != "Collected",
        )
        .order_by(Deposit.created_at.desc())
        .limit(limit)
    ).all()
    return deposits


def get_active_user_deposit(student_id: str):
    return db.session.scalar(
        sa.select(Deposit)
        .options(
            so.load_only(
                Deposit.id,
                Deposit.status,
                Deposit.created_at,
            )
        )
        .where(
            Deposit.student_id == student_id,
            Deposit.status.in_(ACTIVE_DEPOSIT_STATUSES),
        )
        .order_by(Deposit.created_at.desc())
        .limit(1)
    )


def get_completed_user_deposits(student_id: str, limit: int = 10):
    deposits = db.session.scalars(
        sa.select(Deposit)
        .options(
            so.load_only(
                Deposit.id,
                Deposit.status,
                Deposit.created_at,
            ),
            so.selectinload(Deposit.service).load_only(ServiceDetail.item_count),
            so.selectinload(Deposit.items).load_only(ClothingItem.id),
        )
        .where(
            Deposit.student_id == student_id,
            Deposit.status == "Completed",
        )
        .order_by(Deposit.created_at.desc())
        .limit(limit)
    ).all()
    return deposits


def get_all_deposits():
    deposits = db.session.scalars(
        sa.select(Deposit)
        .options(
            so.load_only(
                Deposit.id,
                Deposit.student_id,
                Deposit.staff_id,
                Deposit.status,
                Deposit.created_at,
            )
        )
        .order_by(Deposit.created_at.desc())
    ).all()
    return deposits


def get_deposit_for_view(deposit_id: int):
    return db.session.scalar(
        sa.select(Deposit)
        .options(
            so.selectinload(Deposit.items),
            so.joinedload(Deposit.service),
            so.joinedload(Deposit.staff),
            so.joinedload(Deposit.student),
        )
        .where(Deposit.id == deposit_id)
    )


def _delete_deposit_with_archived_images(deposit: Deposit):
    image_filenames = {
        item.image_filename
        for item in deposit.items
        if item.image_filename
    }

    db.session.delete(deposit)
    db.session.commit()

    for image_filename in image_filenames:
        delete_image_if_unused(image_filename)


def delete_user_deposit_if_allowed(deposit_id: int, student_id: str):
    deposit = db.session.scalar(
        sa.select(Deposit)
        .options(so.selectinload(Deposit.items))
        .where(
            Deposit.id == deposit_id,
            Deposit.student_id == student_id,
        )
    )

    if deposit is None:
        return None, "Deposit not found."

    if deposit.status != "Not Given":
        return None, "Only deposits with status Not Given can be removed."

    _delete_deposit_with_archived_images(deposit)
    return True, None


def update_deposit_items_from_wardrobe(
    deposit_id: int,
    student_id: str,
    wardrobe_item_ids: list[int],
):
    deposit = db.session.scalar(
        sa.select(Deposit)
        .options(
            so.selectinload(Deposit.items),
            so.joinedload(Deposit.service),
        )
        .where(
            Deposit.id == deposit_id,
            Deposit.student_id == student_id,
        )
    )

    if deposit is None:
        return None, "Deposit not found."

    if deposit.status != "Not Given":
        return None, "You can only edit clothes while the deposit status is Not Given."

    unique_wardrobe_item_ids = list(dict.fromkeys(wardrobe_item_ids or []))
    if not unique_wardrobe_item_ids:
        _delete_deposit_with_archived_images(deposit)
        return None, None

    if len(unique_wardrobe_item_ids) > 10:
        return None, "Maximum 10 wardrobe items allowed per deposit."

    selected_wardrobe_items = db.session.scalars(
        sa.select(WardrobeItem)
        .options(
            so.load_only(
                WardrobeItem.id,
                WardrobeItem.name,
                WardrobeItem.image_filename,
            )
        )
        .where(
            WardrobeItem.user_id == student_id,
            WardrobeItem.id.in_(unique_wardrobe_item_ids),
        )
    ).all()

    wardrobe_item_map = {item.id: item for item in selected_wardrobe_items}
    if len(wardrobe_item_map) != len(unique_wardrobe_item_ids):
        return None, "One or more selected wardrobe items could not be found."

    old_image_filenames = {
        item.image_filename
        for item in deposit.items
        if item.image_filename
    }

    deposit.items.clear()

    for wardrobe_item_id in unique_wardrobe_item_ids:
        wardrobe_item = wardrobe_item_map[wardrobe_item_id]
        archived_image_filename = None

        if wardrobe_item.image_filename:
            archived_image_filename = duplicate_stored_image(
                wardrobe_item.image_filename,
                folder_name=f"{student_id}_deposits",
            )

        deposit.items.append(
            ClothingItem(
                description=wardrobe_item.name,
                image_filename=archived_image_filename or wardrobe_item.image_filename,
            )
        )

    total_items = len(deposit.items)
    if deposit.service is None:
        deposit.service = ServiceDetail(item_count=total_items)
    else:
        deposit.service.item_count = total_items

    db.session.commit()

    for image_filename in old_image_filenames:
        delete_image_if_unused(image_filename)

    return deposit, None


def assign_staff_to_deposit(deposit_id: int, staff_id: int):
    deposit = db.session.get(Deposit, deposit_id)
    if deposit is None:
        return None, "Deposit not found."

    staff = db.session.get(Staff, staff_id)
    if staff is None:
        return None, "Invalid staff member."

    deposit.staff_id = staff.id
    db.session.commit()

    return deposit, None


def update_deposit_status(deposit_id: int, new_status: str):
    deposit = db.session.get(Deposit, deposit_id)
    if deposit is None:
        return None, "Deposit not found."

    if new_status not in ALLOWED_STATUSES:
        return None, f"Invalid status. Must be one of: {', '.join(ALLOWED_STATUSES)}"

    deposit.status = new_status
    db.session.commit()

    return deposit, None
