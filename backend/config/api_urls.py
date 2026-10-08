from django.urls import include, path

from config.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/", include("accounts.urls")),
    path("", include("stores.urls")),
    path("", include("catalog.urls")),
    path("", include("accounts.address_urls")),
    path("", include("cart.urls")),
    path("", include("orders.urls")),
]
