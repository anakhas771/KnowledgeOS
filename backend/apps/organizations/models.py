from django.db import models


class Organization(models.Model):
    """
    Represents an isolated KnowledgeOS tenant.
    """

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name