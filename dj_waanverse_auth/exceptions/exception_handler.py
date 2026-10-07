from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

NON_FIELD = "non_field_errors"


def _to_text(value):
    """
    DRF returns {"identifier": ["msg"]}. Collapse each list of messages into one
    string so the client gets {"identifier": "msg"}. Nested dicts are handled too.
    """
    if isinstance(value, dict):
        return {key: _to_text(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        parts = [_to_text(item) for item in value]
        if all(isinstance(p, str) for p in parts):
            return " ".join(parts)  # e.g. several password validator messages
        return parts  # list of dicts (many=True serializers)
    return str(value)


def exception_handler(exc, context):
    """
    Every handled error comes back as:
        {"message": {"<field>": "<text>", ...}}
    Errors that don't belong to a field go under "non_field_errors".
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # unhandled exception -> normal 500

    data = response.data

    if isinstance(exc, ValidationError):
        message = (
            _to_text(data) if isinstance(data, dict) else {NON_FIELD: _to_text(data)}
        )
    else:
        # 401 / 403 / 404 / 429 ...: DRF gives {"detail": "..."}
        detail = data.get("detail", data) if isinstance(data, dict) else data
        message = {NON_FIELD: _to_text(detail)}

    response.data = {"msg": message}
    return response
