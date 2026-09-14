from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.documents.models import Document, DocumentChunk
from apps.documents.services.embeddings import embed_texts
from apps.organizations.models import Organization


EVALUATION_ORG_NAME = "KnowledgeOS Retrieval Evaluation"
EVALUATION_ORG_SLUG = "knowledgeos-retrieval-evaluation"
EVALUATION_EMAIL = "retrieval-evaluation@knowledgeos.local"
EVALUATION_USERNAME = "retrieval_evaluation"


DOCUMENTS = {
    "KnowledgeOS Overview": [
        (
            "KnowledgeOS is an enterprise knowledge intelligence "
            "platform that centralizes organizational knowledge and "
            "provides semantic search and AI-assisted answers."
        ),
        (
            "KnowledgeOS uses document ingestion, text extraction, "
            "chunking, vector embeddings, PostgreSQL with pgvector, "
            "and local language-model generation."
        ),
    ],
    "Authentication and RBAC": [
        (
            "KnowledgeOS authentication uses JWT-based authentication "
            "for API access. Users authenticate before accessing "
            "protected knowledge endpoints."
        ),
        (
            "KnowledgeOS supports organization roles including "
            "administrator, manager, developer, employee, and guest. "
            "Role-based permissions control access to protected actions."
        ),
    ],
    "Document Processing": [
        (
            "Uploaded documents are processed asynchronously. The "
            "processing pipeline extracts text, normalizes it, splits "
            "the text into chunks, generates embeddings, and stores "
            "retrieval-ready chunks."
        ),
        (
            "Document processing supports common knowledge formats "
            "including TXT, Markdown, PDF, DOCX, and XLSX."
        ),
    ],
    "Tenant Isolation": [
        (
            "KnowledgeOS enforces tenant isolation by associating "
            "documents with an organization and filtering retrieval "
            "queries using the authenticated user's organization."
        ),
        (
            "Clients do not choose the organization used for knowledge "
            "retrieval. The organization context comes from the "
            "authenticated user."
        ),
    ],
    "Search and Retrieval": [
        (
            "Semantic search converts a user query into a 384-dimensional "
            "embedding and retrieves similar document chunks using "
            "pgvector cosine similarity."
        ),
        (
            "KnowledgeOS uses an HNSW vector index to support scalable "
            "approximate nearest-neighbor retrieval while ranking "
            "results by similarity."
        ),
    ],
    "Authorization and Permissions": [
        (
            "Authorization determines which actions an authenticated "
            "KnowledgeOS user may perform. Permissions are evaluated "
            "after authentication and are based on the user's role."
        ),
        (
            "Role-based authorization separates identity verification "
            "from permission checks. A valid JWT identifies the user, "
            "while authorization rules determine access to protected "
            "operations."
        ),
    ],
    "Organization Membership": [
        (
            "A KnowledgeOS user belongs to an organization. The "
            "organization relationship is stored on the authenticated "
            "user and establishes the tenant context for knowledge access."
        ),
        (
            "Organization membership is different from application roles. "
            "Membership determines which tenant a user belongs to, while "
            "roles determine which protected actions the user may perform."
        ),
    ],
    "Document Extraction": [
        (
            "Document extraction converts uploaded files into readable "
            "text before downstream processing. The extracted content "
            "becomes the input for normalization and chunk creation."
        ),
        (
            "Extraction is an ingestion-stage operation. It prepares "
            "content from supported document formats so the processing "
            "pipeline can generate searchable text chunks."
        ),
    ],
    "Chunking and Embeddings": [
        (
            "Chunking divides extracted document text into smaller "
            "retrieval units. Each chunk can then be converted into a "
            "vector embedding for semantic search."
        ),
        (
            "KnowledgeOS stores embeddings alongside document chunks. "
            "The embedding represents the semantic content used for "
            "vector similarity retrieval."
        ),
    ],
    "Ingestion Pipeline": [
        (
            "The ingestion pipeline moves uploaded knowledge through "
            "extraction, normalization, chunking, embedding generation, "
            "and storage before it becomes available for retrieval."
        ),
        (
            "Asynchronous ingestion separates document processing from "
            "the request that uploads the file, allowing retrieval-ready "
            "knowledge to be prepared in the background."
        ),
    ],
    "Vector Database": [
        (
            "KnowledgeOS uses PostgreSQL with pgvector to store document "
            "embeddings and perform vector similarity operations."
        ),
        (
            "The vector database layer supports cosine-distance searches "
            "over document embeddings and uses an HNSW index for "
            "approximate nearest-neighbor retrieval."
        ),
    ],
    "Semantic Search": [
        (
            "Semantic search represents a user's query as an embedding "
            "and compares it with stored document embeddings to identify "
            "conceptually similar knowledge."
        ),
        (
            "Semantic retrieval can find relevant content even when the "
            "query uses wording different from the source document."
        ),
    ],
    "AI Assistant Architecture": [
        (
            "The KnowledgeOS assistant combines retrieved knowledge "
            "context with a language model to generate answers grounded "
            "in organizational documents."
        ),
        (
            "The assistant depends on an ingestion and retrieval pipeline "
            "before generation. Documents must become searchable context "
            "before the language model can answer questions from them."
        ),
    ],
    "Knowledge Retrieval Architecture": [
        (
            "Knowledge retrieval connects query embedding, vector "
            "similarity search, document chunks, and organization "
            "filtering into a single retrieval flow."
        ),
        (
            "Retrieval results are produced from stored document chunks "
            "rather than directly querying the language model for company "
            "knowledge."
        ),
    ],
    "API Security": [
        (
            "Protected KnowledgeOS API endpoints require authenticated "
            "requests. JWT authentication establishes the identity used "
            "for access control and organization-aware retrieval."
        ),
        (
            "API security combines authentication, authorization, and "
            "tenant-aware filtering so protected knowledge operations "
            "remain scoped to the requesting user."
        ),
    ],
}


class Command(BaseCommand):
    help = "Create the deterministic corpus used for retrieval evaluation."

    def handle(self, *args, **options):
        with transaction.atomic():
            organization, _ = Organization.objects.get_or_create(
                slug=EVALUATION_ORG_SLUG,
                defaults={"name": EVALUATION_ORG_NAME},
            )

            user, _ = User.objects.get_or_create(
                username=EVALUATION_USERNAME,
                defaults={
                    "email": EVALUATION_EMAIL,
                    "organization": organization,
                    "role": User.Role.ADMIN,
                    "is_active": True,
                },
            )

            if user.organization_id != organization.id:
                user.organization = organization
                user.save(update_fields=["organization"])

            for title, contents in DOCUMENTS.items():
                document, _ = Document.objects.get_or_create(
                    organization=organization,
                    title=title,
                    defaults={
                        "file": f"documents/evaluation/{title.lower().replace(' ', '-')}.txt",
                        "file_type": "text/plain",
                        "file_size": 0,
                        "uploaded_by": user,
                        "status": Document.Status.COMPLETED,
                    },
                )

                if document.uploaded_by_id != user.id:
                    document.uploaded_by = user

                document.status = Document.Status.COMPLETED
                document.save(
                    update_fields=["uploaded_by", "status", "updated_at"]
                )

                DocumentChunk.objects.filter(document=document).delete()

                embeddings = embed_texts(contents)

                DocumentChunk.objects.bulk_create(
                    [
                        DocumentChunk(
                            document=document,
                            chunk_index=index,
                            content=content,
                            embedding=embedding,
                        )
                        for index, (content, embedding) in enumerate(
                            zip(contents, embeddings),
                            start=1,
                        )
                    ]
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Seeded '{title}' "
                        f"(document_id={document.id}, chunks={len(contents)})"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "\nRetrieval evaluation corpus seeded successfully."
            )
        )
        self.stdout.write(
            f"Organization: {organization.name} "
            f"(id={organization.id}, slug={organization.slug})"
        )