from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "api/v1/",
        include("apps.common.urls"),
    ),

    path(
        "api/v1/auth/",
        include("apps.accounts.api.urls"),
    ),

    path(
        "api/v1/",
        include("apps.documents.urls"),
    ),

    path(
        "api/v1/knowledge/",
        include("apps.knowledge.urls"),
    ),
]
urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)