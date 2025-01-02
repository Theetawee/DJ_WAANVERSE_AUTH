from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("v1/auth/", include("dj_waanverse_auth.urls")),
]
