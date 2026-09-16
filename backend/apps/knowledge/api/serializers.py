from rest_framework import serializers
from apps.knowledge.models import Conversation, Message

# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        required=True, 
        allow_blank=False,
        trim_whitespace=True,
        max_length=1000
    )
    limit = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20
    )
    min_similarity = serializers.FloatField(
        required=False,
        default=None,
        min_value=0.0,
        max_value=1.0
    )

class SearchResultChunkSerializer(serializers.Serializer):
    chunk_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    content = serializers.CharField()
    score = serializers.FloatField()

class SearchMetaSerializer(serializers.Serializer):
    embedding_ms = serializers.IntegerField()
    retrieval_ms = serializers.IntegerField()
    total_ms = serializers.IntegerField()

class SearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    results = SearchResultChunkSerializer(many=True)
    meta = SearchMetaSerializer()


# ---------------------------------------------------------------------------
# Conversation serializers
# ---------------------------------------------------------------------------

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "created_at")

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "created_at", "updated_at", "messages")
        read_only_fields = ("id", "created_at", "updated_at")


# ---------------------------------------------------------------------------
# Ask (RAG) endpoint
# ---------------------------------------------------------------------------

class AskRequestSerializer(serializers.Serializer):
    """
    Validates the RAG ask request.
    Only ``query`` is accepted from the client.
    organization_id is ALWAYS derived from request.user — never from the payload.
    """
    query = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=2000,
    )
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
