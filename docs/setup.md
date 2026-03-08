1. pip install dj_waanverse_auth
2. Add `dj_waanverse_auth` to `INSTALLED_APPS`
3. REST_FRAMEWORK = {
   "DEFAULT_AUTHENTICATION_CLASSES": (
   "dj_waanverse_auth.authentication.JWTAuthentication",
   ),
   }

4. add url path(f"{api_url}/auth/", include("dj_waanverse_auth.urls")),
5. python manage.py migrate
6. add WAANVERSE_AUTH_CONFIG = {
   "PUBLIC_KEY_PATH": "",
   "PRIVATE_KEY_PATH": "",
   "PLATFORM_NAME": "Barabara Safaris",
   }
Check settings for more settings