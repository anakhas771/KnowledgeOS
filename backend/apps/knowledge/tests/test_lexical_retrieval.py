from django.test import TestCase

from apps.accounts.models import User
from apps.documents.models import Document, DocumentChunk
from apps.knowledge.services.lexical import search_lexical_chunks
from apps.organizations.models import Organization


class LexicalRetrievalTestCase(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Lexical Org A",
            slug="lexical-org-a",
        )
        self.org_b = Organization.objects.create(
            name="Lexical Org B",
            slug="lexical-org-b",
        )

        self.user_a = User.objects.create_user(
            username="lexical_user_a",
            email="lexical-a@test.local",
            password="testpassword",
            organization=self.org_a,
            role=User.Role.DEVELOPER,
        )
        self.user_b = User.objects.create_user(
            username="lexical_user_b",
            email="lexical-b@test.local",
            password="testpassword",
            organization=self.org_b,
            role=User.Role.DEVELOPER,
        )

        self.doc_a = Document.objects.create(
            organization=self.org_a,
            title="Authentication Guide",
            file="documents/test/auth.txt",
            uploaded_by=self.user_a,
        )
        self.doc_b = Document.objects.create(
            organization=self.org_b,
            title="Other Organization Authentication",
            file="documents/test/other-auth.txt",
            uploaded_by=self.user_b,
        )

        self.chunk_a = DocumentChunk.objects.create(
            document=self.doc_a,
            chunk_index=1,
            content=(
                "JWT authentication protects API access for "
                "authenticated users."
            ),
        )

        self.chunk_b = DocumentChunk.objects.create(
            document=self.doc_b,
            chunk_index=1,
            content=(
                "JWT authentication is used by another organization."
            ),
        )

    def test_lexical_search_returns_matching_chunks(self):
        results = search_lexical_chunks(
            organization_id=self.org_a.id,
            query="JWT authentication",
            limit=5,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["chunk_id"],
            self.chunk_a.id,
        )
        self.assertGreater(results[0]["score"], 0)

    def test_tenant_isolation(self):
        results = search_lexical_chunks(
            organization_id=self.org_a.id,
            query="JWT authentication",
            limit=5,
        )

        document_ids = {
            result["document_id"]
            for result in results
        }

        self.assertIn(self.doc_a.id, document_ids)
        self.assertNotIn(self.doc_b.id, document_ids)

    def test_non_matching_query_returns_no_results(self):
        results = search_lexical_chunks(
            organization_id=self.org_a.id,
            query="Kubernetes deployment",
            limit=5,
        )

        self.assertEqual(results, [])