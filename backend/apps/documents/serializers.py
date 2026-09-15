import os

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

        ext = os.path.splitext(value.name)[1].lower()
        supported_extensions = {".txt", ".md", ".pdf", ".docx", ".xlsx"}

        if ext not in supported_extensions:
            raise serializers.ValidationError(
                f"Unsupported file extension. Supported extensions are: {', '.join(sorted(supported_extensions))}"
            )

        header = value.read(1024)
        value.seek(0)

        if ext == ".pdf":
            if not header.startswith(b"%PDF-"):
                raise serializers.ValidationError("Invalid PDF file signature.")
        elif ext in {".docx", ".xlsx"}:
            if not header.startswith(b"PK\x03\x04"):
                raise serializers.ValidationError(f"Invalid {ext[1:].upper()} file signature.")
        elif ext in {".txt", ".md"}:
            if b"\x00" in header:
                raise serializers.ValidationError("Text files cannot contain binary content.")
            try:
                header.decode("utf-8")
            except UnicodeDecodeError:
                raise serializers.ValidationError("Text files must be valid UTF-8.")

        return value
