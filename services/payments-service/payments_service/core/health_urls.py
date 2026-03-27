from django.urls import path
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health(request):
    checks = {"service": "payments-service", "status": "ok", "checks": {}}
    try:
        connection.ensure_connection()
        checks["checks"]["postgres"] = "ok"
    except Exception as e:
        checks["checks"]["postgres"] = str(e)
        checks["status"] = "degraded"
    try:
        cache.set("hc", "1", 5)
        checks["checks"]["redis"] = "ok"
    except Exception as e:
        checks["checks"]["redis"] = str(e)
        checks["status"] = "degraded"
    return JsonResponse(checks, status=200 if checks["status"] == "ok" else 503)


urlpatterns = [path("", health, name="health")]
