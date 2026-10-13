from django.contrib.auth import get_user_model
from django.test import TestCase
from django_dynamic_fixture import G

from ..models import Label, MailboxEntry, Message, Thread
from ..services import send_message

User = get_user_model()


class SendMessageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = G(User, email='alice@example.com')
        cls.bob = G(User, email='bob@example.com')
        cls.carol = G(User, email='carol@example.com')
        cls.dave = G(User, email='dave@example.com')

    def send(self, **kwargs):
        defaults = {
            'sender': self.alice,
            'subject': 'Hello',
            'body': 'Hi there',
            'recipients': {'to': [self.bob]},
        }
        return send_message(**{**defaults, **kwargs})

    @staticmethod
    def label_names(entry):
        return {label.name for label in entry.labels.all()}

    def test_it_creates_a_new_thread_when_none_is_given(self):
        # === Act ===
        message = self.send()

        # === Assert ===
        self.assertEqual(Thread.objects.count(), 1)
        self.assertEqual(message.thread, Thread.objects.get())
        self.assertIsNone(message.parent)

    def test_it_reuses_the_given_thread_and_sets_the_parent(self):
        # === Arrange ===
        first = self.send()

        # === Act ===
        reply = self.send(sender=self.bob, recipients={'to': [self.alice]}, thread=first.thread, parent=first)

        # === Assert ===
        self.assertEqual(Thread.objects.count(), 1)
        self.assertEqual(reply.thread, first.thread)
        self.assertEqual(reply.parent, first)

    def test_it_saves_the_message_fields(self):
        # === Act ===
        message = self.send(subject='Plan', body='Let us meet')

        # === Assert ===
        message.refresh_from_db()
        self.assertEqual(message.sender, self.alice)
        self.assertEqual(message.subject, 'Plan')
        self.assertEqual(message.body, 'Let us meet')

    def test_it_creates_one_entry_per_participant_with_the_right_role(self):
        # === Act ===
        message = self.send(recipients={'to': [self.bob], 'cc': [self.carol], 'bcc': [self.dave]})

        # === Assert ===
        roles = {entry.user: entry.role for entry in MailboxEntry.objects.filter(message=message)}
        self.assertEqual(
            roles,
            {
                self.alice: MailboxEntry.Role.SENDER,
                self.bob: MailboxEntry.Role.TO,
                self.carol: MailboxEntry.Role.CC,
                self.dave: MailboxEntry.Role.BCC,
            },
        )

    def test_it_works_when_cc_and_bcc_are_not_given(self):
        # === Act ===
        message = self.send(recipients={'to': [self.bob]})

        # === Assert ===
        self.assertEqual(MailboxEntry.objects.filter(message=message).count(), 2)

    def test_it_marks_the_senders_entry_as_read_and_the_rest_as_unread(self):
        # === Act ===
        message = self.send(recipients={'to': [self.bob], 'cc': [self.carol], 'bcc': [self.dave]})

        # === Assert ===
        for entry in MailboxEntry.objects.filter(message=message):
            self.assertEqual(entry.is_read, entry.user == self.alice, entry.user.email)

    def test_it_labels_the_senders_entry_sent_and_recipients_entries_inbox(self):
        # === Act ===
        message = self.send(recipients={'to': [self.bob], 'cc': [self.carol], 'bcc': [self.dave]})

        # === Assert ===
        for entry in MailboxEntry.objects.filter(message=message).prefetch_related('labels'):
            expected = {'sent'} if entry.user == self.alice else {'inbox'}
            self.assertEqual(self.label_names(entry), expected, entry.user.email)

    def test_it_uses_the_system_labels_of_each_user(self):
        # === Act ===
        message = self.send()

        # === Assert ===
        bob_entry = MailboxEntry.objects.get(message=message, user=self.bob)
        label = bob_entry.labels.get()
        self.assertEqual(label.user, self.bob)
        self.assertTrue(label.is_system)

    def test_it_rolls_back_everything_if_a_recipient_has_no_system_labels(self):
        # === Arrange ===
        Label.objects.filter(user=self.bob, name='inbox').delete()

        # === Act ===
        # The exact exception depends on the implementation (Label.DoesNotExist or KeyError)
        with self.assertRaises((Label.DoesNotExist, KeyError)):
            self.send()

        # === Assert ===
        self.assertEqual(Thread.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(MailboxEntry.objects.count(), 0)
