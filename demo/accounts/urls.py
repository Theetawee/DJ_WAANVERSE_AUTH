from django.urls import path
from .views import check_username_availability


urlpatterns = [
    path(
        "check",
        check_username_availability,
        name="check_username_avalibility",
    ),
]
