import random
import string
from datetime import datetime


import secrets


def generate_verification_code():
    return f"{secrets.randbelow(900000) + 100000}"


def generate_username():
    timestamp = datetime.now().strftime("%m%d%H%M%S%f")[:-3]
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    random_joint = random.choice(["_", "-"])
    return f"user{random_joint}{timestamp}{random_suffix}"
