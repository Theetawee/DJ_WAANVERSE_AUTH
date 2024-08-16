# Installation

## Requirements

Before installing `dj_waanverse_auth`, ensure your environment meets the following requirements:

- **Python 3.11+**: The package is fully compatible with Python 3.11 and later versions, leveraging the latest features and improvements.
- **Django 5.1+**: Ensure you have Django 5.1 or a more recent version installed, as the package takes advantage of advanced features introduced in Django 5.x.
- **Django REST Framework 3.15+**: This package integrates seamlessly with Django REST Framework 3.15 and above, ensuring robust API management and security.
- **SimpleJWT 5.3+**: Required for comprehensive JWT management, including token generation, validation, and refresh mechanisms.


!!! note "Note"

    While `dj_waanverse_auth` is designed to automatically install all necessary dependencies, it's advisable to manually verify the installation of these critical packages if you encounter any issues. Ensuring that your environment meets these requirements is essential for a smooth setup and operation.



## Quickstart

To get started with `dj_waanverse_auth`, follow these steps:

### 1. Install the Package

First, install the package using pip:

```bash
pip install dj_waanverse_auth
```

### 2. Configure Django Settings
Assuming you have a Django project already set up, you need to make several updates to your settings.py file:

a. SMTP Settings
Set up SMTP settings for your project to enable email functionalities such as password resets and account verification. For detailed guidance, refer to the <a href="https://docs.djangoproject.com/en/4.1/topics/email/" target="_blank" rel="noopener noreferrer">Django Email documentation</a>

b. Add to Installed Apps
Include dj_waanverse_auth in your INSTALLED_APPS list:

```python
INSTALLED_APPS = [
    ...
    'dj_waanverse_auth',
    ...
]
```
c. Authentication Backends
Add the custom authentication backend provided by dj_waanverse_auth:

```python
AUTHENTICATION_BACKENDS = [
    "dj_waanverse_auth.backends.CustomAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]
```
d. SimpleJWT Configuration
Configure the JWT settings. The `SIMPLE_JWT` dictionary handles the lifetime of access and refresh tokens and cookie lifetimes. For additional configurations, refer to the <a href="https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html" target="_blank" rel="noopener noreferrer">SimpleJWT documentation</a>
.

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}
```
e. REST Framework Configuration
Set dj_waanverse_auth as the default authentication class in Django REST Framework:

```python
REST_FRAMEWORK = {
    ...
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_waanverse_auth.backends.JWTAuthentication",
    ),
    ...
}
```
f. Middleware Configuration
Add the CookiesHandlerMiddleware to your middleware stack:

```python
MIDDLEWARE = [
    ...
    "dj_waanverse_auth.middleware.CookiesHandlerMiddleware",
    ...
]
```
By following these steps, you'll have dj_waanverse_auth integrated into your Django project and ready to handle authentication using JWT.

### 3. URL Configuration
Additionally, add this to your project urls.py:

```python
urlpatterns = [
    ...
    path('auth/', include('dj_waanverse_auth.urls')),
    ...
]
```
## Post Installation
In your Django root execute the command below to create your database tables:

```bash
python manage.py migrate
```
