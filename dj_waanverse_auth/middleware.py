from rest_framework import status

from .settings import auth_config


class WaanverseAuthMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            if response.status_code == status.HTTP_401_UNAUTHORIZED:
                response.delete_cookie(
                    auth_config.access_token_cookie,
                    domain=auth_config.cookie_domain,
                    path=auth_config.cookie_path,
                )
                response.delete_cookie(
                    auth_config.refresh_token_cookie,
                    domain=auth_config.cookie_domain,
                    path=auth_config.cookie_path,
                )

        except Exception:
            pass
        return response
