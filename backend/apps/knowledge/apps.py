import os

from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.knowledge"

    def ready(self):
        """
        Warm the embedding model when the Django development server
        starts its serving process.

        The RUN_MAIN check prevents the Django autoreloader parent
        process from loading the model unnecessarily.
        """

        if os.getenv("KNOWLEDGEOS_WARM_EMBEDDING_MODEL") != "1":
            return

        if os.getenv("RUN_MAIN") != "true":
            return

        from apps.documents.services.embeddings import (
            get_embedding_model,
        )

        get_embedding_model()