from django.db import models


class OrganizationOwnedModel(models.Model):
    """
    Abstract base model for resources owned by a KnowledgeOS organization.

    Any concrete model inheriting from this class must provide an
    organization relationship automatically.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_records",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True