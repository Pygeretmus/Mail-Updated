from django.contrib.auth import get_user_model
from django.test import TestCase
from django_dynamic_fixture import G
from rest_framework.exceptions import ValidationError

from ..models import Message
from ..services import build_reply_recipients, send_message

User = get_user_model()


class BuildReplyRecipientsTest(TestCase):
    def setUp(self):
        self.alice = G(User, email='alice@example.com')
        self.bob = G(User, email='bob@example.com')
        self.carol = G(User, email='carol@example.com')
        self.dave = G(User, email='dave@example.com')
        self.erin = G(User, email='erin@example.com')

        # alice -> to: bob, erin; cc: carol; bcc: dave
        self.message = send_message(
            sender=self.alice,
            subject='Plan',
            body='Let us meet',
            recipients={'to': [self.bob, self.erin], 'cc': [self.carol], 'bcc': [self.dave]},
        )

    @staticmethod
    def users(result, key):
        # Order is not guaranteed and 'cc' may be absent for a plain reply
        return set(result.get(key, []))

    def reload_message(self):
        return Message.objects.get(pk=self.message.pk)

    # --- regular cases ---

    def test_plain_reply_goes_only_to_the_sender(self):
        # === Act ===
        result = build_reply_recipients(self.message, self.bob)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.alice})
        self.assertEqual(self.users(result, 'cc'), set())

    def test_reply_all_goes_to_everybody_except_the_replying_user_and_bcc(self):
        # === Act ===
        result = build_reply_recipients(self.message, self.bob, reply_all=True)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.alice, self.erin})
        self.assertEqual(self.users(result, 'cc'), {self.carol})

    def test_reply_all_by_a_cc_recipient_goes_to_the_sender_and_all_to_recipients(self):
        # === Act ===
        result = build_reply_recipients(self.message, self.carol, reply_all=True)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.alice, self.bob, self.erin})
        self.assertEqual(self.users(result, 'cc'), set())

    def test_bcc_recipient_replying_to_all_does_not_expose_themselves(self):
        # === Act ===
        result = build_reply_recipients(self.message, self.dave, reply_all=True)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.alice, self.bob, self.erin})
        self.assertEqual(self.users(result, 'cc'), {self.carol})

    def test_replying_to_own_message_goes_to_the_original_to_recipients(self):
        # === Act ===
        result = build_reply_recipients(self.message, self.alice)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.bob, self.erin})
        self.assertEqual(self.users(result, 'cc'), set())

    def test_reply_all_to_own_message_keeps_to_and_cc_and_never_bcc(self):
        # === Act ===
        result = build_reply_recipients(self.message, self.alice, reply_all=True)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.bob, self.erin})
        self.assertEqual(self.users(result, 'cc'), {self.carol})

    def test_it_never_includes_the_replying_user_or_bcc_recipients(self):
        # === Act & Assert ===
        for user in (self.alice, self.bob, self.carol, self.erin):
            for reply_all in (False, True):
                with self.subTest(user=user.email, reply_all=reply_all):
                    result = build_reply_recipients(self.message, user, reply_all=reply_all)

                    everyone = self.users(result, 'to') | self.users(result, 'cc')
                    self.assertNotIn(user, everyone)
                    self.assertNotIn(self.dave, everyone)

    def test_plain_reply_to_a_deleted_sender_raises_a_validation_error(self):
        # === Arrange ===
        self.alice.delete()

        # === Act & Assert ===
        with self.assertRaises(ValidationError):
            build_reply_recipients(self.reload_message(), self.bob)

    def test_reply_all_after_the_sender_was_deleted_goes_to_the_remaining_recipients(self):
        # === Arrange ===
        self.alice.delete()

        # === Act ===
        result = build_reply_recipients(self.reload_message(), self.bob, reply_all=True)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.erin})
        self.assertEqual(self.users(result, 'cc'), {self.carol})

    def test_it_never_returns_none_as_a_recipient(self):
        # === Arrange ===
        self.alice.delete()

        # === Act ===
        result = build_reply_recipients(self.reload_message(), self.bob, reply_all=True)

        # === Assert ===
        self.assertNotIn(None, self.users(result, 'to') | self.users(result, 'cc'))

    def test_reply_all_raises_when_nobody_is_left_to_reply_to(self):
        # === Arrange ===
        message = send_message(sender=self.alice, subject='Hi', body='x', recipients={'to': [self.bob]})
        self.alice.delete()

        # === Act & Assert ===
        with self.assertRaises(ValidationError):
            build_reply_recipients(Message.objects.get(pk=message.pk), self.bob, reply_all=True)

    def test_reply_all_promotes_cc_to_to_if_no_to_recipients_are_left(self):
        # === Arrange ===
        message = send_message(
            sender=self.alice, subject='Hi', body='x', recipients={'to': [self.bob], 'cc': [self.carol]}
        )
        self.alice.delete()

        # === Act ===
        result = build_reply_recipients(Message.objects.get(pk=message.pk), self.bob, reply_all=True)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.carol})
        self.assertEqual(self.users(result, 'cc'), set())

    def test_reply_all_to_own_message_promotes_cc_to_to_if_to_recipient_was_deleted(self):
        # === Arrange ===
        message = send_message(
            sender=self.bob, subject='Hi', body='x', recipients={'to': [self.erin], 'cc': [self.carol]}
        )
        self.erin.delete()

        # === Act ===
        result = build_reply_recipients(Message.objects.get(pk=message.pk), self.bob, reply_all=True)

        # === Assert ===
        self.assertEqual(self.users(result, 'to'), {self.carol})
        self.assertEqual(self.users(result, 'cc'), set())

    def test_plain_reply_does_not_promote_cc(self):
        # === Arrange ===
        message = send_message(
            sender=self.bob, subject='Hi', body='x', recipients={'to': [self.erin], 'cc': [self.carol]}
        )
        self.erin.delete()

        # === Act & Assert ===
        with self.assertRaises(ValidationError):
            build_reply_recipients(Message.objects.get(pk=message.pk), self.bob)
