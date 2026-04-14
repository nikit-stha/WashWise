import re


def is_valid_email(email: str) -> bool:
    if not email:
        return False

    email = email.strip().lower()
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return re.match(pattern, email) is not None


def is_thapar_email(email: str) -> bool:
    if not email:
        return False

    email = email.strip().lower()
    return email.endswith("@thapar.edu")


def is_valid_password(password: str) -> bool:
    if not password:
        return False

    password = password.strip()

    if len(password) <= 6:
        return False

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False

    return True