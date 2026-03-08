Google OAuth requires adding

GOOGLE_CLIENT_ID: str
GOOGLE_CLIENT_SECRET: str

    GOOGLE_REDIRECT_URI: str

Endpoints

/google/auth/ - returns the redirect url

/google/redirect/ - returns the access token

can be customized.
