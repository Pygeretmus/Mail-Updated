import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils.timezone import now

from .constants import TRASH_RETENTION_DAYS
from .models import MailboxEntry, Message, Thread

logger = logging.getLogger(__name__)


def _count(deleted_per_model: dict, model) -> int:
    """QuerySet.delete() returns (total, {'app.Model': count}); the key is missing when nothing was deleted."""
    return deleted_per_model.get(model._meta.label, 0)


@shared_task(queue='mail')
def remove_old_deleted_mailbox_entries():
    cutoff = now() - timedelta(days=TRASH_RETENTION_DAYS)

    with transaction.atomic():
        _, per_model = MailboxEntry.objects.filter(deleted_at__lte=cutoff).delete()
        entries = _count(per_model, MailboxEntry)

        _, per_model = Message.objects.filter(entries__isnull=True).delete()
        messages = _count(per_model, Message)

        _, per_model = Thread.objects.filter(messages__isnull=True).delete()
        threads = _count(per_model, Thread)

    logger.info('Trash cleanup finished: removed %d entries, %d messages, %d threads', entries, messages, threads)
    return {'entries': entries, 'messages': messages, 'threads': threads}
