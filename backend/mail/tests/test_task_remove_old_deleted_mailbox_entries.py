from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django_dynamic_fixture import G

from ..constants import TRASH_RETENTION_DAYS
from ..models import MailboxEntry, Message, Thread
from ..services import send_message
from ..tasks import remove_old_deleted_mailbox_entries

User = get_user_model()

OLD = TRASH_RETENTION_DAYS + 1  # days ago: past the retention period
RECENT = TRASH_RETENTION_DAYS - 1  # days ago: still within the retention period


class RemoveOldDeletedMailboxEntriesTaskTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = G(User, email='alice@example.com')
        cls.bob = G(User, email='bob@example.com')

    def send(self, **kwargs):
        defaults = {
            'sender': self.alice,
            'subject': 'Hi',
            'body': 'Body',
            'recipients': {'to': [self.bob]},
        }
        return send_message(**{**defaults, **kwargs})

    @staticmethod
    def trash(message, user, days_ago):
        MailboxEntry.objects.filter(message=message, user=user).update(
            deleted_at=timezone.now() - timedelta(days=days_ago)
        )

    def test_it_removes_entries_trashed_longer_than_retention_period(self):
        # === Arrange ===
        message = self.send()
        self.trash(message, self.alice, OLD)

        # === Act ===
        remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertFalse(MailboxEntry.objects.filter(message=message, user=self.alice).exists())

    def test_it_keeps_entries_trashed_recently(self):
        # === Arrange ===
        message = self.send()
        self.trash(message, self.alice, RECENT)

        # === Act ===
        remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertTrue(MailboxEntry.objects.filter(message=message, user=self.alice).exists())

    def test_it_keeps_entries_that_are_not_trashed(self):
        # === Arrange ===
        message = self.send()

        # === Act ===
        remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertEqual(MailboxEntry.objects.filter(message=message).count(), 2)

    def test_it_keeps_message_and_thread_while_someone_still_has_an_entry(self):
        # === Arrange ===
        message = self.send()
        self.trash(message, self.alice, OLD)  # Bob did not delete his copy

        # === Act ===
        remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())
        self.assertTrue(Thread.objects.filter(pk=message.thread_id).exists())
        self.assertTrue(MailboxEntry.objects.filter(message=message, user=self.bob).exists())

    def test_it_removes_message_and_thread_when_all_entries_are_gone(self):
        # === Arrange ===
        message = self.send()
        self.trash(message, self.alice, OLD)
        self.trash(message, self.bob, OLD)

        # === Act ===
        remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertFalse(Message.objects.filter(pk=message.pk).exists())
        self.assertFalse(Thread.objects.filter(pk=message.thread_id).exists())

    def test_it_keeps_thread_and_replies_when_only_the_first_message_is_gone(self):
        # === Arrange ===
        first = self.send()
        reply = self.send(
            sender=self.bob,
            recipients={'to': [self.alice]},
            thread=first.thread,
            parent=first,
        )
        self.trash(first, self.alice, OLD)
        self.trash(first, self.bob, OLD)

        # === Act ===
        remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertFalse(Message.objects.filter(pk=first.pk).exists())
        reply.refresh_from_db()
        self.assertIsNone(reply.parent)  # Message.parent is SET_NULL
        self.assertTrue(Thread.objects.filter(pk=first.thread_id).exists())

    def test_it_removes_orphan_messages_and_threads_left_from_before(self):
        # === Arrange ===
        orphan = self.send()
        MailboxEntry.objects.filter(message=orphan).delete()  # e.g. left by an older version of the cleanup

        # === Act ===
        remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertFalse(Message.objects.filter(pk=orphan.pk).exists())
        self.assertFalse(Thread.objects.filter(pk=orphan.thread_id).exists())

    def test_it_returns_how_many_objects_were_removed(self):
        # === Arrange ===
        message = self.send()
        self.trash(message, self.alice, OLD)
        self.trash(message, self.bob, OLD)

        # === Act ===
        result = remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertEqual(result, {'entries': 2, 'messages': 1, 'threads': 1})

    def test_it_returns_zeros_when_there_is_nothing_to_remove(self):
        # === Act ===
        result = remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertEqual(result, {'entries': 0, 'messages': 0, 'threads': 0})

    def test_it_logs_how_many_objects_were_removed(self):
        # === Arrange ===
        message = self.send()
        self.trash(message, self.alice, OLD)
        self.trash(message, self.bob, OLD)

        # === Act ===
        with self.assertLogs('mail.tasks', level='INFO') as logs:
            remove_old_deleted_mailbox_entries()

        # === Assert ===
        self.assertIn('removed 2 entries, 1 messages, 1 threads', logs.output[0])
