import secrets


def generate_verification_code():
    return f"{secrets.randbelow(900000) + 100000}"
