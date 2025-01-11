from rest_framework.throttling import SimpleRateThrottle


class EmailVerificationThrottle(SimpleRateThrottle):
    rate = "1/min"

    def get_cache_key(self, request, view):
        email = request.data.get("email_address")
        if email:
            return f"email_verification_rate_limit_{email}"
        return None
