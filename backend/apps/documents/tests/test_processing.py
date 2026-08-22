from pathlib import Path

from django.core.files.base import ContentFile
from django.test import TestCase

from apps.accounts.models import User
from apps.documents.models import Document, DocumentChunk
from apps.documents.tasks import process_document_task
from apps.organizations.models import Organization


class DocumentProcessingTests(TestCase):

    def test_document_is_extracted_and_chunked(self):
        organization = Organization.objects.create(
            name="Processing Organization",
            slug="processing-organization",
        )

        user = User.objects.create_user(
            username="processor",
            email="processor@test.local",
            password="TestPassword123!",
            organization=organization,
            role=User.Role.ADMIN,
        )

        document = Document.objects.create(
            organization=organization,
            uploaded_by=user,
            title="Processing Test",
            file_type="text/plain",
        )

        document.file.save(
            "processing.txt",
            ContentFile(
                (
                    "KnowledgeOS processing test. "
                    "This content should be extracted "
                    "and converted into retrieval chunks."
                ).encode("utf-8")
            ),
            save=True,
        )

        process_document_task.apply(
            args=[document.id],
        )

        document.refresh_from_db()

        self.assertEqual(
            document.status,
            Document.Status.COMPLETED,
        )

        self.assertTrue(
            document.extracted_text,
        )

        self.assertGreater(
            DocumentChunk.objects.filter(
                document=document,
            ).count(),
            0,
        )
