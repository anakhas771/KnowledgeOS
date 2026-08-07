from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.accounts.services.authentication import AuthenticationService

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    organization_slug = serializers.SlugField(max_length=255)
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )

        return value

    def validate_organization_slug(self, value):
        from apps.organizations.models import Organization

        if Organization.objects.filter(slug=value).exists():
            raise serializers.ValidationError(
                "An organization with this slug already exists."
            )

        return value

    def create(self, validated_data):
        return AuthenticationService.register_user(
            **validated_data
        )

class LoginSerializer(TokenObtainPairSerializer):
    """Authenticate a user and return JWT tokens."""

    pass

class UserProfileSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "organization",
        ]

    def get_organization(self, obj):
        if not obj.organization:
            return None

        return {
            "id": obj.organization.id,
            "name": obj.organization.name,
            "slug": obj.organization.slug,
        }