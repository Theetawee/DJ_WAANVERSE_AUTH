from functools import wraps

from rest_framework import status
from rest_framework.exceptions import APIException


class AuthenticatedAccessDenied(APIException):
    """Custom exception for authenticated users trying to access unauthenticated-only views."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This endpoint is only accessible to unauthenticated users."
    default_code = "authenticated_access_denied"


def unauthenticated_only(view_func):
    """
    Decorator to restrict access to unauthenticated users only.

    Args:
        view_func: The view function to be decorated

    Returns:
        Wrapped view function that checks authentication status

    Raises:
        AuthenticatedAccessDenied: If an authenticated user tries to access the view

    Usage:
        @unauthenticated_only
        def my_view(request):
            return Response({"message": "Hello, anonymous user!"})
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated
        if request.user and request.user.is_authenticated:
            raise AuthenticatedAccessDenied()

        return view_func(request, *args, **kwargs)

    return _wrapped_view
