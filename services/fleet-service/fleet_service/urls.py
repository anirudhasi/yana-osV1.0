from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/fleet/",    include("fleet_service.core.urls")),
    path("api/schema/",      SpectacularAPIView.as_view(),  name="schema"),
    path("api/docs/",        SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("health/",          include("fleet_service.core.health_urls")),
]
