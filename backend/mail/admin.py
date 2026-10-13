from django.contrib import admin
from django.db.models import Count
from django.utils import timezone

from .models import Label, MailboxEntry, Message, Thread


class MessageInline(admin.TabularInline):
    """Read-only preview of messages inside a thread"""

    model = Message
    fields = ('subject', 'sender', 'created_at')
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'message_count')
    readonly_fields = ('created_at',)
    inlines = (MessageInline,)

    def get_queryset(self, request):
        # Annotate instead of calling .messages.count() per row in the
        # changelist — avoids one extra query per thread (N+1).
        return super().get_queryset(request).annotate(_message_count=Count('messages'))

    @admin.display(description='Messages')
    def message_count(self, obj):
        return obj._message_count


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'sender', 'parent', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('sender__email',)
    autocomplete_fields = ('sender', 'parent')
    readonly_fields = ('created_at',)
    list_select_related = ('sender',)


@admin.register(MailboxEntry)
class MailboxEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message_subject', 'role', 'is_read', 'deleted_at')
    list_filter = ('role', 'is_read', 'deleted_at')
    search_fields = ('user__email', 'message__subject')
    autocomplete_fields = ('user', 'message', 'labels')
    list_select_related = ('user', 'message')
    actions = ('mark_as_read', 'mark_as_unread', 'soft_delete', 'restore')

    @admin.display(description='Subject', ordering='message__subject')
    def message_subject(self, obj):
        return obj.message.subject

    @admin.action(description='Mark selected entries as read')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description='Mark selected entries as unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)

    @admin.action(description='Move selected entries to trash')
    def soft_delete(self, request, queryset):
        queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())

    @admin.action(description='Restore selected entries from trash')
    def restore(self, request, queryset):
        queryset.update(deleted_at=None)


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'is_system')
    list_filter = ('is_system',)
    search_fields = ('name', 'user__email')
    autocomplete_fields = ('user',)
    list_select_related = ('user',)

    def get_readonly_fields(self, request, obj=None):
        # System labels are protected from edits/deletes
        if obj is not None and obj.is_system:
            return ('name', 'is_system', 'user')
        return ()

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)
