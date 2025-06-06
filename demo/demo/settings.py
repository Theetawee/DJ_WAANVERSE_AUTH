"""
Django settings for demo project.

Generated by 'django-admin startproject' using Django 5.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-$+_3!g^!g28llr2m$0m52pyf95&o%rsu%oj6sx*d9%o87b#iz6"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

AUTH_USER_MODEL = "accounts.Account"


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dj_waanverse_auth",
    "rest_framework",
    "accounts",
]

MIDDLEWARE = [
    "dj_waanverse_auth.middleware.auth.IPBlockerMiddleware",
    "dj_waanverse_auth.middleware.client_hints.ClientHintsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "dj_waanverse_auth.middleware.auth.AuthCookieMiddleware",
]

ROOT_URLCONF = "demo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "demo.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "dj_waanverse_auth.backends.AuthenticationBackend",
]


# Email settings
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# use console backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = os.environ.get("SMTP_EMAIL", "email@gmail.com")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD", "test-password")
EMAIL_USE_TLS = True


WAANVERSE_AUTH_CONFIG = {
    "PUBLIC_KEY_PATH": os.path.join(BASE_DIR, "secrets/public_key.pem"),
    "PRIVATE_KEY_PATH": os.path.join(BASE_DIR, "secrets/private_key.pem"),
    "REFRESH_TOKEN_COOKIE_MAX_AGE": timedelta(days=30),
    "ACCESS_TOKEN_COOKIE_MAX_AGE": timedelta(minutes=30),
    "BASIC_ACCOUNT_SERIALIZER": "accounts.serializers.BasicAccountSerializer",
    "DISPOSABLE_EMAIL_DOMAINS": [
        "tempmail.com",
        "throwawaymail.com",
        "guerrillamail.com",
        "mailinator.com",
    ],
    "ENABLE_ADMIN_PANEL": True,
    "REGISTRATION_SERIALIZER": "accounts.serializers.SignupSerializer",
    "PHONE_NUMBER_VERIFICATION_SERIALIZER": "accounts.serializers.PhoneSerializer",
    "MFA_DEBUG_CODE": "123456",
    "PLATFORM_NAME": "Demo Platform",
    "EMAIL_THREADING_ENABLED": False,
    "UPDATE_ACCOUNT_SERIALIZER": "accounts.serializers.UpdateAccountSerializer",
    "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID"),
    "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_SECRET_ID"),
    "GOOGLE_REDIRECT_URI": os.environ.get("GOOGLE_REDIRECT_URI"),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_waanverse_auth.authentication.JWTAuthentication",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}
