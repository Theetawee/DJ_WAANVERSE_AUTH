from importlib import import_module
from django.db import transaction
from dj_waanverse_auth import settings
from dj_waanverse_auth.utils.generators import generate_verification_code
from dj_waanverse_auth.models import VerificationCode


def get_send_code_function():
    """
    Retrieve the function to send a verification code via SMS.

    Users should override this function in settings by providing
    a dotted path to their custom SMS sending function.

    Returns:
        func: The function that accepts (phone_number: str, code: str)

    Raises:
        ValueError: If SEND_PHONE_VERIFICATION_CODE_FUNC is not defined in settings.
        ImportError: If the module or function cannot be imported.
    """
    dotted_path = settings.send_phone_verification_code_func
    if not dotted_path:
        raise ValueError("SEND_PHONE_VERIFICATION_CODE_FUNC is not defined in settings")

    try:
        module_path, func_name = dotted_path.rsplit(".", 1)
        module = import_module(module_path)
        func = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not import send code function '{dotted_path}': {e}")

    return func


def send_phone_verification_code(user) -> None:
    """
    Generate a verification code for a user's phone number, save it in the database,
    and send it via the configured SMS function.

    Args:
        user: The user instance with `phone_number` attribute.

    Raises:
        ValueError: If the user has no phone number or it is already verified.
        Exception: Any exception raised by the SMS sending function.
    """
    if not user.phone_number or user.phone_number_verified:
        raise ValueError("User has no phone number or it is already verified.")

    code = generate_verification_code()

    with transaction.atomic():
        VerificationCode.objects.filter(phone_number=user.phone_number).delete()
        VerificationCode.objects.create(phone_number=user.phone_number, code=code)

    send_func = get_send_code_function()
    send_func(user.phone_number, code)
