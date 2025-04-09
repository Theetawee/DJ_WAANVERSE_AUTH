from django.utils.module_loading import import_string


def get_serializer_class(class_path: str):
    """
    Retrieve a serializer class given its string path.

    Args:
        class_path (str): Full dotted path to the serializer class.
                          Example: 'dj_waanverse_auth.serializers.Basic_Serializer'

    Returns:
        class: The serializer class.

    Raises:
        ImportError: If the class cannot be imported.
    """
    try:
        return import_string(class_path)
    except ImportError as e:
        raise ImportError(f"Could not import serializer class '{class_path}': {e}")
