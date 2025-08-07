from importlib import import_module
from dj_waanverse_auth import settings


def get_send_code_function():
    dotted_path = settings.send_phone_verification_code_func
    if not dotted_path:
        raise ValueError(
            "SEND_PHONE_VERIFICATION_CODE_FUNC not defined in WAANVERSE_AUTH settings"
        )

    module_path, func_name = dotted_path.rsplit(".", 1)
    try:
        module = import_module(module_path)
        func = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not import send code function '{dotted_path}': {e}")

    return func
