import io
import os
import re
import shutil
from uuid import uuid4

import sqlalchemy as sa
from flask import current_app
from PIL import Image, UnidentifiedImageError

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_IMAGE_SIZE_BYTES = 1024 * 1024
MIN_IMAGE_DIMENSION = 600


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, folder_name=None):
    if not allowed_file(file.filename):
        return None

    filename = f"{uuid4().hex}.webp"
    relative_path = filename

    if folder_name:
        safe_folder_name = _sanitize_folder_name(folder_name)
        relative_path = os.path.join(safe_folder_name, filename)

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        image = Image.open(file.stream)
        image.load()
    except (UnidentifiedImageError, OSError):
        return None

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    for quality in (82, 74, 66, 58, 50, 42, 34):
            encoded = _encode_image(image, quality=quality)
            if len(encoded.getbuffer()) <= MAX_IMAGE_SIZE_BYTES:
                _save_buffer(encoded, path)
                return relative_path

    resized_image = image
    while min(resized_image.size) > MIN_IMAGE_DIMENSION:
        width = max(int(resized_image.width * 0.85), MIN_IMAGE_DIMENSION)
        height = max(int(resized_image.height * 0.85), MIN_IMAGE_DIMENSION)
        resized_image = resized_image.resize((width, height), Image.Resampling.LANCZOS)

        for quality in (50, 42, 34, 26):
            encoded = _encode_image(resized_image, quality=quality)
            if len(encoded.getbuffer()) <= MAX_IMAGE_SIZE_BYTES:
                _save_buffer(encoded, path)
                return relative_path

    encoded = _encode_image(resized_image, quality=22)
    if len(encoded.getbuffer()) <= MAX_IMAGE_SIZE_BYTES:
        _save_buffer(encoded, path)
        return relative_path

    return None


def duplicate_stored_image(relative_path, folder_name=None):
    if not relative_path:
        return None

    source_path = _resolve_upload_path(relative_path)
    if source_path is None or not os.path.exists(source_path):
        return None

    extension = os.path.splitext(relative_path)[1].lower() or ".webp"
    filename = f"{uuid4().hex}{extension}"
    copied_relative_path = filename

    if folder_name:
        copied_relative_path = os.path.join(_sanitize_folder_name(folder_name), filename)

    destination_path = os.path.join(current_app.config["UPLOAD_FOLDER"], copied_relative_path)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    shutil.copy2(source_path, destination_path)

    return copied_relative_path


def delete_image_if_unused(relative_path):
    if not relative_path:
        return False

    from app.extensions import db
    from app.models.clothing_item import ClothingItem
    from app.models.wardrobe_item import WardrobeItem

    wardrobe_references = db.session.scalar(
        sa.select(sa.func.count())
        .select_from(WardrobeItem)
        .where(WardrobeItem.image_filename == relative_path)
    ) or 0

    clothing_references = db.session.scalar(
        sa.select(sa.func.count())
        .select_from(ClothingItem)
        .where(ClothingItem.image_filename == relative_path)
    ) or 0

    if wardrobe_references + clothing_references > 0:
        return False

    image_path = _resolve_upload_path(relative_path)
    if image_path is None or not os.path.exists(image_path):
        return False

    os.remove(image_path)
    _remove_empty_upload_dirs(os.path.dirname(image_path))
    return True


def _sanitize_folder_name(folder_name):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", folder_name.strip())
    return cleaned or "anonymous"


def _resolve_upload_path(relative_path):
    upload_root = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
    candidate_path = os.path.abspath(os.path.join(upload_root, relative_path))

    try:
        if os.path.commonpath([upload_root, candidate_path]) != upload_root:
            return None
    except ValueError:
        return None

    return candidate_path


def _remove_empty_upload_dirs(directory_path):
    upload_root = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
    current_path = os.path.abspath(directory_path)

    while current_path != upload_root:
        try:
            if os.listdir(current_path):
                break
        except FileNotFoundError:
            break

        os.rmdir(current_path)
        current_path = os.path.dirname(current_path)


def _encode_image(image, quality):
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=quality, method=6)
    buffer.seek(0)
    return buffer


def _save_buffer(buffer, path):
    with open(path, "wb") as output_file:
        output_file.write(buffer.getvalue())
