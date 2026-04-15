from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
import sqlalchemy as sa

from app.extensions import app, db
from app.models.user import User
from app.models.wardrobe_item import WardrobeItem
from app.utils.clothing_types import CLOTHING_TYPES, normalize_clothing_type
from app.utils.file_utils import save_image, delete_image_if_unused


@app.route("/user/wardrobe", methods=["GET", "POST"])
@login_required
def user_wardrobe():
    if not isinstance(current_user, User):
        flash("Access denied: Users only.")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        clothing_type = normalize_clothing_type(request.form.get("clothing_type"))
        image = next(
            (uploaded_file for uploaded_file in request.files.getlist("image")
             if uploaded_file and uploaded_file.filename),
            None,
        )

        if not name:
            flash("Clothing name is required.")
            return redirect(url_for("user_wardrobe"))

        if clothing_type is None:
            flash("Please select a valid clothing type.")
            return redirect(url_for("user_wardrobe"))

        if image is None:
            flash("Please upload an image.")
            return redirect(url_for("user_wardrobe"))

        saved_filename = save_image(image, folder_name=current_user.user_id)
        if saved_filename is None:
            flash("Unable to process image. Use a valid png, jpg, jpeg, or webp image.")
            return redirect(url_for("user_wardrobe"))

        item = WardrobeItem(
            user_id=current_user.user_id,
            name=name,
            clothing_type=clothing_type,
            image_filename=saved_filename
        )

        db.session.add(item)
        db.session.commit()

        flash("Wardrobe item added successfully.")
        return redirect(url_for("user_wardrobe"))

    wardrobe_items = db.session.scalars(
        sa.select(WardrobeItem)
        .options(
            sa.orm.load_only(
                WardrobeItem.id,
                WardrobeItem.name,
                WardrobeItem.clothing_type,
                WardrobeItem.image_filename,
                WardrobeItem.created_at,
            )
        )
        .where(WardrobeItem.user_id == current_user.user_id)
        .order_by(WardrobeItem.created_at.desc())
    ).all()

    return render_template(
        "wardrobe.html",
        title="My Wardrobe",
        wardrobe_items=wardrobe_items,
        clothing_types=CLOTHING_TYPES,
    )


@app.route("/user/wardrobe/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_wardrobe_item(item_id):
    if not isinstance(current_user, User):
        flash("Access denied: Users only.")
        return redirect(url_for("index"))

    item = WardrobeItem.query.get(item_id)

    if item is None:
        flash("Wardrobe item not found.")
        return redirect(url_for("user_wardrobe"))

    if item.user_id != current_user.user_id:
        flash("Access denied.")
        return redirect(url_for("user_wardrobe"))

    image_filename = item.image_filename
    db.session.delete(item)
    db.session.commit()
    delete_image_if_unused(image_filename)

    flash("Wardrobe item deleted successfully.")
    return redirect(url_for("user_wardrobe"))
