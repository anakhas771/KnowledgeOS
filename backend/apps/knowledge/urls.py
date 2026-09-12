from django.urls import path
from .api.views import AskAPIView, SearchAPIView

app_name = "knowledge"

urlpatterns = [
    path("search/", SearchAPIView.as_view(), name="search"),
    path("ask/", AskAPIView.as_view(), name="ask"),
]
