from django.conf import settings
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
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh_token = response.data.get("refresh")
            if refresh_token:
                response.set_cookie(
                    key="refresh",
                    value=refresh_token,
                    httponly=True,
                    secure=getattr(settings, "JWT_REFRESH_COOKIE_SECURE", False),
                    samesite="Lax",
                )
                del response.data["refresh"]
        return response
        

class RefreshTokenView(TokenRefreshView):
    """Refresh an access token."""

    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh")
        
        # SimpleJWT expects refresh token in request body
        if refresh_token:
            # We copy request.data because it might be immutable (QueryDict)
            if hasattr(request.data, '_mutable'):
                request.data._mutable = True
            request.data['refresh'] = refresh_token
            
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            new_refresh = response.data.get("refresh")
            if new_refresh:
                response.set_cookie(
                    key="refresh",
                    value=new_refresh,
                    httponly=True,
                    secure=getattr(settings, "JWT_REFRESH_COOKIE_SECURE", False),
                    samesite="Lax",
                )
                del response.data["refresh"]
        return response

class LogoutView(APIView):
    """Logout the user and clear the refresh cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie("refresh", samesite="Lax")
        return response
    
class MeView(APIView):
    """
    Return current authenticated user information.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)

        return Response(serializer.data)


