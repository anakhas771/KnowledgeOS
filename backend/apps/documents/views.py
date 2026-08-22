from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import OrganizationQuerysetMixin

from .models import Document
from .serializers import DocumentSerializer
from .tasks import process_document_task

class DocumentViewSet(
    OrganizationQuerysetMixin,
    viewsets.ModelViewSet,
):
    """
    Tenant-isolated document API.
    """

    queryset = Document.objects.all()

    serializer_class = DocumentSerializer

    permission_classes = [IsAuthenticated]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def perform_create(self, serializer):
        user = self.request.user
        uploaded_file = self.request.FILES["file"]

        document = serializer.save(
            organization=user.organization,
            uploaded_by=user,
            file_type=uploaded_file.content_type,
            file_size=uploaded_file.size,
        )

        process_document_task.delay(
            document.id,
        )

    def destroy(self, request, *args, **kwargs):
        document = self.get_object()

        if request.user.role not in {
            request.user.Role.ADMIN,
            request.user.Role.MANAGER,
        }:
            return Response(
                {
                    "detail": (
                        "Only administrators and managers "
                        "can delete documents."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().destroy(request, *args, **kwargs)