import re


HOSTEL_CHOICES = (
    ("A", "Agira Hall ( A )"),
    ("B", "Amritam Hall ( B )"),
    ("C", "Prithvi Hall ( C )"),
    ("D", "Neeram Hall ( D )"),
    ("E", "Vasudha Hall - Block E ( E )"),
    ("G", "Vasudha Hall - Block G ( G )"),
    ("H", "Vyan Hall ( H )"),
    ("I", "Ira Hall ( I )"),
    ("J", "Tejas Hall ( J )"),
    ("K", "Ambaram Hall ( K )"),
    ("L", "Viyat Hall ( L )"),
    ("M", "Anantam Hall ( M )"),
    ("N", "Ananta Hall ( N )"),
    ("O", "Vyom Hall ( O )"),
    ("PG", "Dhriti Hall ( PG )"),
    ("Q", "Vahni Hall ( Q )"),
    ("FRFG", "Hostel-FRF/G ( FRF/G )"),
)

HOSTEL_LABELS = dict(HOSTEL_CHOICES)
VALID_HOSTEL_CODES = tuple(HOSTEL_LABELS)


def normalize_hostel_code(hostel_code: str) -> str:
    hostel_code = (hostel_code or "").strip().upper()
    return re.sub(r"[^A-Z0-9]", "", hostel_code)


def normalize_hostel_codes(hostel_codes) -> tuple[str, ...]:
    if isinstance(hostel_codes, str):
        raw_codes = hostel_codes.split(",")
    else:
        raw_codes = hostel_codes or []

    selected_codes = {
        normalize_hostel_code(hostel_code)
        for hostel_code in raw_codes
        if normalize_hostel_code(hostel_code)
    }

    return tuple(
        hostel_code
        for hostel_code in VALID_HOSTEL_CODES
        if hostel_code in selected_codes
    )


def serialize_hostel_codes(hostel_codes) -> str:
    return ",".join(normalize_hostel_codes(hostel_codes))


def is_valid_hostel_code(hostel_code: str) -> bool:
    return normalize_hostel_code(hostel_code) in HOSTEL_LABELS


def get_hostel_label(hostel_code: str) -> str:
    normalized_code = normalize_hostel_code(hostel_code)
    return HOSTEL_LABELS.get(normalized_code, hostel_code)


def get_hostel_labels(hostel_codes) -> str:
    labels = [
        HOSTEL_LABELS[hostel_code]
        for hostel_code in normalize_hostel_codes(hostel_codes)
    ]
    return ", ".join(labels) if labels else "No hostel selected"


def get_hostel_summary(hostel_codes) -> str:
    normalized_codes = normalize_hostel_codes(hostel_codes)

    if not normalized_codes:
        return "No hostel selected"

    if len(normalized_codes) == len(VALID_HOSTEL_CODES):
        return "All hostels"

    if len(normalized_codes) <= 2:
        return ", ".join(HOSTEL_LABELS[hostel_code] for hostel_code in normalized_codes)

    return f"{len(normalized_codes)} hostels"
