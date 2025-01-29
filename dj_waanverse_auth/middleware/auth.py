from dj_waanverse_auth.authentication import JWTAuthentication


class AuthCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.auth_class = JWTAuthentication()

    def __call__(self, request):
        response = self.get_response(request)
        if request.META.get("HTTP_X_COOKIES_TO_DELETE", ""):
            response = self.auth_class.delete_marked_cookies(response, request)

        return response
