import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.documents.models import Document, DocumentChunk
from apps.organizations.models import Organization
from apps.accounts.models import User

class ChunkEvidenceAPITestCase(APITestCase):
    def setUp(self):
        self.org1 = Organization.objects.create(name="Org1", slug="org1")
        self.user1 = User.objects.create_user(
            username="user1", email="u1@test.com", password="pwd",
            organization=self.org1, role=User.Role.DEVELOPER
        )
        self.doc1 = Document.objects.create(organization=self.org1, title="Doc1", uploaded_by=self.user1)
        self.chunk1 = DocumentChunk.objects.create(document=self.doc1, chunk_index=1, content="Exact evidence here")

        self.org2 = Organization.objects.create(name="Org2", slug="org2")
        self.user2 = User.objects.create_user(
            username="user2", email="u2@test.com", password="pwd",
            organization=self.org2, role=User.Role.DEVELOPER
        )
        self.doc2 = Document.objects.create(organization=self.org2, title="Doc2", uploaded_by=self.user2)
        self.chunk2 = DocumentChunk.objects.create(document=self.doc2, chunk_index=1, content="Secret evidence")

    def _url(self, chunk_id):
        return reverse("knowledge:knowledge-chunk-evidence", kwargs={"chunk_id": chunk_id})

    def test_unauthenticated_access(self):
        url = self._url(self.chunk1.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authorized_same_tenant_access(self):
        self.client.force_authenticate(user=self.user1)
        url = self._url(self.chunk1.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["chunk_id"], self.chunk1.id)
        self.assertEqual(data["document_id"], self.doc1.id)
        self.assertEqual(data["document_title"], "Doc1")
        self.assertEqual(data["content"], "Exact evidence here")
        self.assertNotIn("embedding", data)

    def test_cross_tenant_access_blocked(self):
        # user1 tries to access org2's chunk
        self.client.force_authenticate(user=self.user1)
        url = self._url(self.chunk2.id)
        response = self.client.get(url)
        
        # Must return 404 to avoid leaking existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_chunk_returns_404(self):
        self.client.force_authenticate(user=self.user1)
        url = self._url(999999)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
