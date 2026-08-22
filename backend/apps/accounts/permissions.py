from rest_framework.permissions import BasePermission


class IsOrganizationAdmin(BasePermission):
    """
    Allow access only to KnowledgeOS organization administrators.
    """

    message = "Organization administrator access is required."

    def has_permission(self, request, view):
        user = request.user

        return (
            bool(user and user.is_authenticated)
            and user.is_active
            and user.role == user.Role.ADMIN
        )


class IsOrganizationManager(BasePermission):
    """
    Allow administrators and managers.
    """

    message = "Manager or administrator access is required."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated or not user.is_active:
            return False

        return user.role in {
            user.Role.ADMIN,
            user.Role.MANAGER,
        }


class IsKnowledgeUser(BasePermission):
    """
    Allow users who can access the organizational knowledge base.
    """

    message = "Knowledge base access is required."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated or not user.is_active:
            return False

        return user.role in {
            user.Role.ADMIN,
            user.Role.MANAGER,
            user.Role.DEVELOPER,
            user.Role.EMPLOYEE,
        }


class IsKnowledgeViewer(BasePermission):
    """
    Allow read-only knowledge access, including guests.
    """

    message = "Knowledge base access is required."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated or not user.is_active:
            return False

        return user.role in {
            user.Role.ADMIN,
            user.Role.MANAGER,
            user.Role.DEVELOPER,
            user.Role.EMPLOYEE,
            user.Role.GUEST,
        }
