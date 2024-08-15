from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="DJ Waanverse Auth",
        default_version="v-0.0.0-alpha",
        description="A comprehensive Waanverse Labs Inc.Rest internal package for managing user  authentication and authorization.",
        terms_of_service="https://www.waanverse.com/policies/user-agreement/",
        contact=openapi.Contact(email="software@waanverse.com"),
        license=openapi.License(name="Free to use but restricted"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dj_waanverse_auth.urls")),
    path("", include("accounts.urls")),
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "docs",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
