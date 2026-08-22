from django.test import TestCase
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.documents.models import Document, DocumentChunk
from apps.knowledge.services.retrieval import search_similar_chunks
import numpy as np


class VectorRetrievalTestCase(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Org A", slug="org-a")
        self.org_b = Organization.objects.create(name="Org B", slug="org-b")

        self.user_a = User.objects.create_user(
            username="user_a",
            email="usera@test.local",
            password="testpassword",
            organization=self.org_a,
            role=User.Role.DEVELOPER,
        )

        self.user_b = User.objects.create_user(
            username="user_b",
            email="userb@test.local",
            password="testpassword",
            organization=self.org_b,
            role=User.Role.DEVELOPER,
        )

        self.doc_a = Document.objects.create(
            organization=self.org_a,
            title="Document A",
            uploaded_by=self.user_a,
        )

        self.doc_b = Document.objects.create(
            organization=self.org_b,
            title="Document B",
            uploaded_by=self.user_b,
        )
        
        # Exact same mock embedding for both to test isolation and thresholds
        # Using 384 dimensions
        self.mock_embedding = [0.1] * 384
        self.mock_embedding_normalized = list(np.array(self.mock_embedding) / np.linalg.norm(self.mock_embedding))

        self.chunk_a = DocumentChunk.objects.create(
            document=self.doc_a,
            chunk_index=1,
            content="Content A",
            embedding=self.mock_embedding_normalized
        )

        self.chunk_b = DocumentChunk.objects.create(
            document=self.doc_b,
            chunk_index=1,
            content="Content B",
            embedding=self.mock_embedding_normalized
        )
        
        # A dissimilar chunk
        dissimilar_embedding = [-0.1] * 384
        dissimilar_embedding_normalized = list(np.array(dissimilar_embedding) / np.linalg.norm(dissimilar_embedding))
        
        self.chunk_a_2 = DocumentChunk.objects.create(
            document=self.doc_a,
            chunk_index=2,
            content="Content A 2",
            embedding=dissimilar_embedding_normalized
        )

    def test_tenant_isolation(self):
        # Even though chunk B has identical embedding, it should not be returned for org A
        results = search_similar_chunks(
            organization_id=self.org_a.id,
            query_embedding=self.mock_embedding_normalized,
            limit=5
        )
        
        # Should return chunks from Org A only
        self.assertEqual(len(results), 2)
        
        chunk_ids = [res["chunk_id"] for res in results]
        self.assertIn(self.chunk_a.id, chunk_ids)
        self.assertIn(self.chunk_a_2.id, chunk_ids)
        self.assertNotIn(self.chunk_b.id, chunk_ids)

    def test_threshold_logic(self):
        # The identical embedding should have similarity ~1.0
        # The opposite embedding should have similarity ~ -1.0
        # With threshold 0.0, we should only get the identical one
        results = search_similar_chunks(
            organization_id=self.org_a.id,
            query_embedding=self.mock_embedding_normalized,
            limit=5,
            min_similarity=0.0
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], self.chunk_a.id)
        self.assertGreater(results[0]["score"], 0.9)
