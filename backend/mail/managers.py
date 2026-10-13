from django.db import models
from django.db.models import Prefetch


class MailboxEntryQuerySet(models.QuerySet):
    def with_recipients(self):
        return self.prefetch_related(Prefetch('message__entries', queryset=self.model.objects.select_related('user')))


class MailboxEntryManager(models.Manager):
    def get_queryset(self):
        return MailboxEntryQuerySet(self.model, using=self._db)

    def with_recipients(self):
        return self.get_queryset().with_recipients()
