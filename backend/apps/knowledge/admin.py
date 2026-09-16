from django.contrib import admin
from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'organization', 'created_at', 'updated_at')
    search_fields = ('title', 'user__email', 'organization__name')
    list_filter = ('organization', 'created_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'created_at')
    search_fields = ('content',)
    list_filter = ('role', 'created_at')
