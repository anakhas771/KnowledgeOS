from django.urls import path
from .api.views import SearchAPIView

app_name = "knowledge"

urlpatterns = [
    path("search/", SearchAPIView.as_view(), name="search"),
]
