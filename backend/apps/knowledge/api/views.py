from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.knowledge.services.search import perform_search
from .serializers import SearchRequestSerializer, SearchResponseSerializer


class SearchAPIView(APIView):
    """
    Semantic search over the organization's knowledge chunks.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Validate request payload
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        limit = serializer.validated_data["limit"]
        min_similarity = serializer.validated_data.get("min_similarity")

        # Tenant isolation enforced here:
        # Organization ID must come from the authenticated user, NOT the payload
        organization_id = request.user.organization_id

        # Perform the actual semantic search
        result_data = perform_search(
            organization_id=organization_id,
            query=query,
            limit=limit,
            min_similarity=min_similarity,
        )

        # Serialize and return response
        response_serializer = SearchResponseSerializer(data=result_data)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
