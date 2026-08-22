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