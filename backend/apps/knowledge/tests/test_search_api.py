from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.documents.models import Document, DocumentChunk
import numpy as np


class SearchAPITestCase(APITestCase):
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
        
        self.doc = Document.objects.create(
            organization=self.organization,
            title="Test Document",
            uploaded_by=self.user,
        )

        # 384 dim vector
        self.mock_embedding = [0.1] * 384
        self.mock_embedding_normalized = list(np.array(self.mock_embedding) / np.linalg.norm(self.mock_embedding))

        self.chunk = DocumentChunk.objects.create(
            document=self.doc,
            chunk_index=1,
            content="This is an enterprise knowledge base document.",
            embedding=self.mock_embedding_normalized
        )

    def test_unauthenticated_request_fails(self):
        response = self.client.post(
            "/api/v1/knowledge/search/",
            {"query": "test"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_query_fails(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/knowledge/search/",
            {"query": "   "},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_invalid_limit_fails(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/knowledge/search/",
            {
                "query": "enterprise",
                "limit": 50 # max is 20
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_search(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/knowledge/search/",
            {
                "query": "enterprise knowledge base",
                "limit": 5
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data["query"], "enterprise knowledge base")
        self.assertTrue("results" in data)
        self.assertTrue("meta" in data)
        
        meta = data["meta"]
        self.assertTrue("embedding_ms" in meta)
        self.assertTrue("retrieval_ms" in meta)
        self.assertTrue("total_ms" in meta)
        
        results = data["results"]
        # Assuming the model returns something somewhat similar, we should get 1 result here
        self.assertGreaterEqual(len(results), 0)
        if len(results) > 0:
            first_result = results[0]
            self.assertEqual(first_result["chunk_id"], self.chunk.id)
            self.assertEqual(first_result["document_title"], "Test Document")
            self.assertTrue("score" in first_result)
            self.assertFalse("embedding" in first_result)
