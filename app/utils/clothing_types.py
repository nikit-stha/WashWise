from __future__ import annotations


CLOTHING_TYPES = [
    "Jeans",
    "Pent",
    "Pyjama",
    "Shorts",
    "Shirts",
    "T-Shirts",
    "Kurta/Salwar",
    "Skirt",
    "Dupatta",
    "Bed Sheet",
    "Pillow Cover",
    "Tower/H-Towel",
    "Turban",
    "Upper Hood",
]

VALID_CLOTHING_TYPES = set(CLOTHING_TYPES)


def normalize_clothing_type(value: str | None) -> str | None:
    cleaned_value = " ".join((value or "").split())
    if cleaned_value in VALID_CLOTHING_TYPES:
        return cleaned_value
    return None
