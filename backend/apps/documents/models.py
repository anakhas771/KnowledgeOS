from django.conf import settings
from django.db import models
from pgvector.django import VectorField
from apps.common.models import OrganizationOwnedModel


class Document(OrganizationOwnedModel):
    """
    Represents a knowledge document owned by an organization.
    """

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(
        max_length=255,
    )

    file = models.FileField(
        upload_to="documents/%Y/%m/%d/",
    )

    file_type = models.CharField(
        max_length=100,
        blank=True,
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )

    extracted_text = models.TextField(
        blank=True,
        default="",
    )

    processing_error = models.TextField(
        blank=True,
        default="",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
    )

    def __str__(self):
        return self.title

class DocumentChunk(models.Model):
    """
    A retrieval-ready portion of a processed document.
    """

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
    )

    content = models.TextField()

    chunk_index = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_document_chunk_index",
            ),
        ]

    def __str__(self):
        return f"{self.document.title} - chunk {self.chunk_index}"