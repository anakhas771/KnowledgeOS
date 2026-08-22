from rest_framework.exceptions import NotAuthenticated


class OrganizationQuerysetMixin:
    """
    Restrict queryset results to the authenticated user's organization.

    Intended for DRF generic views/viewsets operating on models that
    contain an `organization` ForeignKey.
    """

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user

        if not user or not user.is_authenticated:
            raise NotAuthenticated(
                "Authentication is required."
            )

        if not user.organization_id:
            return queryset.none()

        return queryset.filter(
            organization_id=user.organization_id,
        )