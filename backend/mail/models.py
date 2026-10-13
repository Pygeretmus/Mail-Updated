from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from .managers import MailboxEntryManager


class Thread(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Thread {self.pk}'


class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='messages')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sent_messages'
    )
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.subject}: {self.created_at}'


class MailboxEntry(models.Model):
    class Role(models.TextChoices):
        SENDER = 'sender'
        TO = 'to'
        CC = 'cc'
        BCC = 'bcc'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mailbox_entries')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='entries')
    role = models.CharField(max_length=6, choices=Role.choices)
    is_read = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    labels = models.ManyToManyField('Label', blank=True, related_name='entries')
    objects = MailboxEntryManager()

    def __str__(self):
        return f'{self.user}: {self.role}'

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=['user', 'message'], name='uniq_entry_per_user_message')
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=['deleted_at'],
                name='mailboxentry_deleted_at_idx',
                condition=models.Q(deleted_at__isnull=False),
            ),
        ]


class Label(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='labels')
    name = models.CharField(max_length=50)
    is_system = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user}: {self.name}'

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint('user', Lower('name'), name='uniq_label_name_ci_per_user'),
        ]
