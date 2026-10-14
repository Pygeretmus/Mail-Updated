from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from ..models import MailboxEntry, Message
from ..services import send_message

User = get_user_model()


class APIMessageReplyViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = G(User, email='alice@example.com')
        cls.bob = G(User, email='bob@example.com')
        cls.carol = G(User, email='carol@example.com')

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(user=self.alice)
        original = send_message(
            sender=self.alice,
            subject='Hi',
            body='b',
            recipients={'to': [self.bob], 'cc': [self.carol]},
        )
        self.original_message_id = original.pk
        self.thread_id = original.thread_id

    def test_it_creates_a_reply_message(self):
        # === Arrange ===
        self.client.force_authenticate(self.bob)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 2)
        reply = Message.objects.exclude(pk=self.original_message_id).get()
        self.assertEqual(reply.sender, self.bob)
        self.assertEqual(reply.body, 'reply body')
        self.assertEqual(reply.parent_id, self.original_message_id)

    def test_it_creates_a_reply_all_message(self):
        # === Arrange ===
        self.client.force_authenticate(self.carol)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body', 'reply_all': True}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 2)
        reply = Message.objects.exclude(pk=self.original_message_id).get()
        self.assertEqual(reply.sender, self.carol)
        self.assertEqual(reply.body, 'reply body')
        self.assertEqual(reply.parent_id, self.original_message_id)
        self.assertEqual(reply.entries.count(), 3)

    def test_it_returns_the_repliers_own_mailbox_entry(self):
        # === Arrange ===
        self.client.force_authenticate(self.bob)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        data = response.json()
        reply = Message.objects.exclude(pk=self.original_message_id).get()
        bob_entry = MailboxEntry.objects.get(message=reply, user=self.bob)
        self.assertEqual(data['id'], bob_entry.pk)
        self.assertEqual(data['role'], MailboxEntry.Role.SENDER)

    def test_it_prefixes_subject_with_re(self):
        # === Arrange ===
        self.client.force_authenticate(self.bob)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        self.assertEqual(response.json()['message']['subject'], 'Re: Hi')

    def test_it_does_not_double_prefix_subject(self):
        # === Arrange ===
        self.client.force_authenticate(self.bob)
        first_reply_url = reverse('mail:message-reply', args=[self.original_message_id])
        self.client.post(first_reply_url, data={'body': 'first reply'}, format='json')
        first_reply_id = Message.objects.exclude(pk=self.original_message_id).get().pk

        self.client.force_authenticate(self.alice)
        second_reply_url = reverse('mail:message-reply', args=[first_reply_id])

        # === Act ===
        response = self.client.post(second_reply_url, data={'body': 'second reply'}, format='json')

        # === Assert ===
        self.assertEqual(response.json()['message']['subject'], 'Re: Hi')

    def test_it_links_to_the_parent_message_by_subject(self):
        # === Arrange ===
        self.client.force_authenticate(self.bob)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        self.assertEqual(response.json()['message']['parent'], self.original_message_id)

    def test_default_reply_goes_only_to_original_sender(self):
        # === Arrange ===
        self.client.force_authenticate(self.bob)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        reply = Message.objects.get(pk=response.json()['message']['id'])
        recipients = set(
            MailboxEntry.objects.filter(message=reply)
            .exclude(role=MailboxEntry.Role.SENDER)
            .values_list('user__email', flat=True)
        )
        self.assertEqual(recipients, {'alice@example.com'})

    def test_reply_all_includes_sender_and_cc_but_not_self(self):
        # === Arrange ===
        self.client.force_authenticate(self.bob)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body', 'reply_all': True}, format='json')

        # === Assert ===
        reply = Message.objects.get(pk=response.json()['message']['id'])
        recipients = set(
            MailboxEntry.objects.filter(message=reply)
            .exclude(role=MailboxEntry.Role.SENDER)
            .values_list('user__email', flat=True)
        )
        self.assertEqual(recipients, {'alice@example.com', 'carol@example.com'})

    def test_it_stays_in_the_same_thread(self):
        # === Arrange ===
        self.client.force_authenticate(self.bob)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        self.assertEqual(response.json()['message']['thread'], self.thread_id)

    def test_it_returns_error_if_message_does_not_involve_the_user(self):
        # === Arrange ===
        stranger = G(User, email='stranger@example.com')
        self.client.force_authenticate(stranger)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_returns_error_for_nonexistent_message(self):
        # === Arrange ===
        url = reverse('mail:message-reply', args=[999999])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': None,
                        'message': 'Authentication credentials were not provided.',
                        'code': 'not_authenticated',
                    }
                ],
                'status': 401,
            },
        )

    @mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {'compose': '2/min'})
    def test_it_returns_error_if_success_requests_too_frequent(self):
        # === Arrange ===
        self.client.force_authenticate(self.carol)
        url = reverse('mail:message-reply', args=[self.original_message_id])

        # === Act ===
        for _ in range(3):
            response = self.client.post(url, data={'body': 'reply body', 'reply_all': True}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(
            response.json(),
            {
                'status': 429,
                'errors': [
                    {
                        'param': None,
                        'message': 'Request was throttled. Expected available in 60 seconds.',
                        'code': 'throttled',
                    }
                ],
            },
        )

    @mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {'compose': '2/min'})
    def test_it_returns_error_if_error_requests_too_frequent(self):
        # === Arrange ===
        url = reverse('mail:message-reply', args=[999999])

        # === Act ===
        for _ in range(3):
            response = self.client.post(url, data={'body': 'reply body'}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(
            response.json(),
            {
                'status': 429,
                'errors': [
                    {
                        'param': None,
                        'message': 'Request was throttled. Expected available in 60 seconds.',
                        'code': 'throttled',
                    }
                ],
            },
        )
