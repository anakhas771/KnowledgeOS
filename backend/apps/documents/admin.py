from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "uploaded_by",
        "file_type",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "file_type",
        "created_at",
    )

    search_fields = (
        "title",
        "organization__name",
        "uploaded_by__username",
        "uploaded_by__email",
    )

    readonly_fields = (
        "file_size",
        "created_at",
        "updated_at",
    )