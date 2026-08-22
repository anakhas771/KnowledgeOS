from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.accounts.permissions import (
    IsOrganizationAdmin,
    IsOrganizationManager,
)

from .jwt import KnowledgeOSTokenSerializer
from .serializers import RegisterSerializer, UserProfileSerializer

class RegisterView(APIView):
    """Register a new organization and its initial user."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "message": "Registration successful.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "organization": user.organization.name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):

    permission_classes = [AllowAny]
    serializer_class = KnowledgeOSTokenSerializer
    

class RefreshTokenView(TokenRefreshView):
    """Refresh an access token."""

    permission_classes = [AllowAny]
    
class MeView(APIView):
    """
    Return current authenticated user information.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)

        return Response(serializer.data)


