from django.urls import path
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
def health(request):
    c = {"service": "maintenance-service", "status": "ok", "checks": {}}
    try:
        connection.ensure_connection(); c["checks"]["postgres"] = "ok"
    except Exception as e:
        c["checks"]["postgres"] = str(e); c["status"] = "degraded"
    try:
        cache.set("hc","1",5); c["checks"]["redis"] = "ok"
    except Exception as e:
        c["checks"]["redis"] = str(e); c["status"] = "degraded"
    return JsonResponse(c, status=200 if c["status"]=="ok" else 503)
urlpatterns = [path("", health, name="health")]
