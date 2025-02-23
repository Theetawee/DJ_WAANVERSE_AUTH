from rest_framework.throttling import SimpleRateThrottle


class EmailVerificationThrottle(SimpleRateThrottle):
    rate = "1/min"

    def get_cache_key(self, request, view):
        email = request.data.get("email_address")
        if email:
            return f"rate_limit_{email}"
        return None


class PhoneVerificationThrottle(SimpleRateThrottle):
    rate = "1/min"

    def get_cache_key(self, request, view):
        phone = request.data.get("phone_number")
        if phone:
            return f"rate_limit_{phone}"
        return None
