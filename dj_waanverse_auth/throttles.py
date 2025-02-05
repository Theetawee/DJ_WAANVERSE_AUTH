from rest_framework.throttling import SimpleRateThrottle


class EmailVerificationThrottle(SimpleRateThrottle):
    rate = "5/min"

    def get_cache_key(self, request, view):
        email = request.data.get("email_address")
        if email:
            return f"rate_limit_{email}"
        return None
