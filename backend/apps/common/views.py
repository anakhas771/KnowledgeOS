from django.db import connection
from django.http import JsonResponse
from django.core.cache import cache


def health_check(request):
    """
    Basic application health check.

    Verifies that the Django application is running
    and that PostgreSQL and Redis are reachable.
    """

    database_status = "healthy"
    redis_status = "healthy"

    try:
        connection.ensure_connection()
    except Exception:
        database_status = "unhealthy"

    try:
        cache.set("health_check", "ok", timeout=10)
        cache.get("health_check")
    except Exception:
        redis_status = "unhealthy"

    overall_status = (
        "healthy"
        if database_status == "healthy" and redis_status == "healthy"
        else "unhealthy"
    )

    return JsonResponse(
        {
            "status": overall_status,
            "service": "KnowledgeOS API",
            "version": "1.0.0",
            "dependencies": {
                "database": database_status,
                "redis": redis_status,
            },
        }
    )