from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    uploaded_by = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    chunk_count = serializers.IntegerField(
        source="chunks.count",
        read_only=True,
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "organization",
            "title",
            "file",
            "file_type",
            "file_size",
            "status",
            "uploaded_by",
            "chunk_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "organization",
            "file_type",
            "file_size",
            "status",
            "uploaded_by",
            "chunk_count",
            "created_at",
            "updated_at",
        ]

    def validate_file(self, value):
        max_size = 10 * 1024 * 1024

        if value.size > max_size:
            raise serializers.ValidationError(
                "File size must not exceed 10 MB."
            )

        return value
