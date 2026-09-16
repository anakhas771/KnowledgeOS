from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api.views import AskAPIView, SearchAPIView, ConversationViewSet, ChunkEvidenceAPIView

router = DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="conversation")

app_name = "knowledge"

urlpatterns = [
    path("search/", SearchAPIView.as_view(), name="knowledge-search"),
    path("ask/", AskAPIView.as_view(), name="knowledge-ask"),
    path("chunks/<int:chunk_id>/", ChunkEvidenceAPIView.as_view(), name="knowledge-chunk-evidence"),
    path("", include(router.urls)),
]
