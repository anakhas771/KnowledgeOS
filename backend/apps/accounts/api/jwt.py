from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class KnowledgeOSTokenSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):

        token = super().get_token(user)

        token["user_id"] = user.id
        token["email"] = user.email
        token["role"] = user.role

        if user.organization:
            token["organization_id"] = user.organization.id

        return token
    