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