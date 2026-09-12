from celery import shared_task
from django.db import transaction

from apps.documents.services.embeddings import embed_texts

from .models import Document, DocumentChunk
from .services.chunker import chunk_text
from .services.processor import process_document


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def process_document_task(self, document_id: int):
    """
    Extract, normalize, chunk, embed, and persist document content.
    """

    document = Document.objects.get(
        pk=document_id,
    )

    document.status = Document.Status.PROCESSING
    document.processing_error = ""

    document.save(
        update_fields=[
            "status",
            "processing_error",
            "updated_at",
        ]
    )

    try:
        text = process_document(
            file_path=document.file.path,
            file_type=document.file_type,
        )

        if not text.strip():
            raise ValueError(
                "No extractable text was found in the document."
            )

        chunks = chunk_text(text)

        if not chunks:
            raise ValueError(
                "Document produced no usable chunks."
            )

        chunk_embeddings = embed_texts(
            [chunk.content for chunk in chunks]
        )

        if len(chunk_embeddings) != len(chunks):
            raise ValueError(
                "Embedding service returned an unexpected "
                "number of embeddings."
            )

        with transaction.atomic():
            DocumentChunk.objects.filter(
                document=document,
            ).delete()

            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        document=document,
                        chunk_index=chunk.index,
                        content=chunk.content,
                        embedding=embedding,
                    )
                    for chunk, embedding in zip(
                        chunks,
                        chunk_embeddings,
                    )
                ]
            )

            document.extracted_text = text
            document.status = Document.Status.COMPLETED
            document.processing_error = ""

            document.save(
                update_fields=[
                    "extracted_text",
                    "status",
                    "processing_error",
                    "updated_at",
                ]
            )

        return {
            "document_id": document.id,
            "status": document.status,
            "chunk_count": len(chunks),
        }

    except Exception as exc:
        document.status = Document.Status.FAILED
        document.processing_error = str(exc)

        document.save(
            update_fields=[
                "status",
                "processing_error",
                "updated_at",
            ]
        )

        raise