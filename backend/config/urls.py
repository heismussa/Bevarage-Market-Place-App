from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from core.views import not_found

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(
            permission_classes=[AllowAny],
            authentication_classes=[],
        ),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            permission_classes=[AllowAny],
            authentication_classes=[],
        ),
        name="docs",
    ),
    # Must stay last among /api/ routes. Returns the JSON 404 even when DEBUG is on.
    re_path(r"^api/", not_found),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.not_found"
handler500 = "core.views.server_error"

admin.site.site_header = "Beverage Delivery Marketplace"
admin.site.site_title = "Beverage Delivery"
admin.site.index_title = "Administration"
