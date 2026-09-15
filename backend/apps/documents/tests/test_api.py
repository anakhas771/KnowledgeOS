from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.documents.models import Document


class DocumentAPITestCase(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
        )

        self.user = User.objects.create_user(
            username="developer",
            email="developer@test.local",
            password="TestPassword123!",
            organization=self.organization,
            role=User.Role.DEVELOPER,
        )

        self.client.force_authenticate(user=self.user)

    def test_authenticated_user_can_upload_document(self):
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            b"KnowledgeOS test content",
            content_type="text/plain",
        )

        response = self.client.post(
            "/api/v1/documents/",
            {
                "title": "Test Document",
                "file": uploaded_file,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        document = Document.objects.get(
            title="Test Document",
        )

        self.assertEqual(
            document.organization,
            self.organization,
        )

        self.assertEqual(
            document.uploaded_by,
            self.user,
        )

    def test_unsupported_file_extension_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "malicious.sh",
            b"#!/bin/bash\necho 'hacked'",
            content_type="application/x-sh",
        )

        response = self.client.post(
            "/api/v1/documents/",
            {
                "title": "Malicious Script",
                "file": uploaded_file,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("file", response.data)
        self.assertIn("Unsupported file extension", str(response.data["file"][0]))
        self.assertFalse(Document.objects.filter(title="Malicious Script").exists())

    def test_valid_extension_but_invalid_signature_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "fake.pdf",
            b"This is not a real PDF file",
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/v1/documents/",
            {
                "title": "Fake PDF",
                "file": uploaded_file,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("file", response.data)
        self.assertIn("Invalid PDF file signature", str(response.data["file"][0]))
        self.assertFalse(Document.objects.filter(title="Fake PDF").exists())

    def test_text_file_with_binary_content_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            b"Start of text\x00\x00\x00End of text",
            content_type="text/plain",
        )

        response = self.client.post(
            "/api/v1/documents/",
            {
                "title": "Binary Text",
                "file": uploaded_file,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("file", response.data)
        self.assertIn("cannot contain binary content", str(response.data["file"][0]))
        self.assertFalse(Document.objects.filter(title="Binary Text").exists())

    def test_authenticated_user_can_list_documents(self):
        Document.objects.create(
            organization=self.organization,
            title="Existing Document",
            file="documents/test.txt",
            uploaded_by=self.user,
        )

        response = self.client.get(
            "/api/v1/documents/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_unauthenticated_user_cannot_list_documents(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            "/api/v1/documents/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        
    def test_user_can_only_see_documents_from_their_organization(self):
        other_organization = Organization.objects.create(
            name="Other Organization",
            slug="other-organization",
        )
    
        Document.objects.create(
            organization=self.organization,
            title="Own Organization Document",
            file="documents/own.txt",
            uploaded_by=self.user,
        )

        Document.objects.create(
            organization=other_organization,
            title="Other Organization Document",
            file="documents/other.txt",
        uploaded_by=self.user,
        )

        response = self.client.get(
            "/api/v1/documents/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        titles = {
            item["title"]
            for item in response.data
        }

        self.assertIn(
            "Own Organization Document",
            titles,
        )

        self.assertNotIn(
            "Other Organization Document",
            titles,
        )