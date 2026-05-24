"""
core/urls.py — Root URL configuration
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse


def health_check(request):
    """
    GET /health/
    Render uses this endpoint to verify the service is alive.
    Returns 200 immediately — no DB query, no auth, no overhead.
    WHY: Without a health check, Render marks deploys as failed even
    when the app is running fine. Keep this response < 1KB and < 100ms.
    """
    return JsonResponse({"status": "ok"})


def cloudinary_health_check(request):
    """
    GET /health/cloudinary/
    Diagnostic endpoint — open in browser to instantly verify Cloudinary
    is configured and working on Render.
    Returns cloud_name, api_key, storage backend, and a live ping result.
    """
    import os
    from django.conf import settings

    cloudinary_url = os.environ.get("CLOUDINARY_URL", "")
    storage_backend = getattr(settings, "DEFAULT_FILE_STORAGE", "django.core.files.storage.FileSystemStorage")
    is_cloudinary = "cloudinary" in storage_backend.lower()

    result = {
        "cloudinary_url_set": bool(cloudinary_url),
        "storage_backend": storage_backend,
        "using_cloudinary_storage": is_cloudinary,
        "cloud_name": None,
        "api_key": None,
        "ping": None,
        "error": None,
    }

    if cloudinary_url:
        try:
            import cloudinary
            import cloudinary.api
            config = cloudinary.config()
            result["cloud_name"] = config.cloud_name
            result["api_key"] = config.api_key
            ping = cloudinary.api.ping()
            result["ping"] = ping.get("status", "unknown")
        except Exception as e:
            result["error"] = str(e)
    else:
        result["error"] = "CLOUDINARY_URL environment variable is NOT set. Images cannot be saved permanently."

    return JsonResponse(result)


urlpatterns = [
    # Render health check — must be fast and unauthenticated
    path("health/", health_check, name="health-check"),
    # Cloudinary diagnostic — visit in browser to verify image storage is working
    path("health/cloudinary/", cloudinary_health_check, name="cloudinary-health"),

    # Django admin
    path("admin/", admin.site.urls),

    # Auth endpoints  →  /api/auth/register/, /api/auth/token/, etc.
    path("api/auth/", include("accounts.urls")),

    # Events & Tickets  →  /api/events/, /api/tickets/purchase/, /api/user/tickets/
    path("api/", include("events.urls")),
]

# Serve uploaded media files during development only.
# In production, Cloudinary handles media — this block is a no-op.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
