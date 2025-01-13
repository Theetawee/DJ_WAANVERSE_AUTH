import logging

from django.http import HttpResponseForbidden
from django.urls import NoReverseMatch, reverse

from dj_waanverse_auth.models import UserDevice
from dj_waanverse_auth.settings import auth_config

logger = logging.getLogger(__name__)


class DeviceAuthMiddleware:
    """
    Middleware to enforce device authentication.
    Checks for device_id in either cookies or headers and validates against the database.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = auth_config.device_auth_excluded_paths + [
            reverse("dj_waanverse_auth_login"),
            reverse("dj_waanverse_auth_signup"),
            reverse("dj_waanverse_auth_initiate_email_verification"),
            reverse("dj_waanverse_auth_mfa_login"),
            reverse("dj_waanverse_auth_initiate_password_reset"),
            reverse("dj_waanverse_auth_reset_password"),
            reverse("dj_waanverse_auth_logout"),
        ]
        try:
            self.admin_url_prefix = reverse("admin:index")
        except NoReverseMatch:
            self.admin_url_prefix = "/admin/"

    def get_device_id(self, request):
        """
        Retrieves device ID from either cookie or header.
        """
        device_id = request.COOKIES.get(auth_config.device_id_cookie_name)
        if not device_id:
            device_id = request.headers.get(auth_config.device_id_header_name)
        return device_id

    def validate_device(self, device_id):
        """
        Validates device ID against the database.
        """
        try:
            device = UserDevice.objects.get(device_id=device_id)
            return device.is_active
        except UserDevice.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error validating device: {str(e)}")
            return False

    def should_skip_auth(self, request):
        """
        Determines if the current path is in the excluded paths or admin URL.
        """
        return any(
            request.path.startswith(path) for path in self.excluded_paths
        ) or request.path.startswith(self.admin_url_prefix)

    def __call__(self, request):
        """
        Middleware entry point for processing requests and responses.
        """
        if self.should_skip_auth(request):
            return self.get_response(request)

        device_id = self.get_device_id(request)

        if not device_id:
            logger.warning("Device ID not found in request")
            return HttpResponseForbidden("identity_error")

        if not self.validate_device(device_id):
            logger.warning(f"Invalid or inactive device ID: {device_id}")
            return HttpResponseForbidden("identity_error")

        response = self.get_response(request)
        return response
