from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from ..models import MailboxEntry, Message

User = get_user_model()


class APIMessageComposeViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = G(User, email='alice@example.com')
        cls.bob = G(User, email='bob@example.com')
        cls.carol = G(User, email='carol@example.com')
        cls.dave = G(User, email='dave@example.com')

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(user=self.alice)
        self.url = reverse('mail:message-compose')

    def test_it_creates_the_message(self):
        # === Act ===
        response = self.client.post(
            self.url,
            data={
                'to': ['bob@example.com'],
                'cc': ['carol@example.com'],
                'bcc': ['dave@example.com'],
                'subject': 'Hello',
                'body': 'Hi there',
            },
            format='json',
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = Message.objects.get()
        self.assertEqual(message.sender, self.alice)
        self.assertEqual(message.subject, 'Hello')
        self.assertEqual(message.body, 'Hi there')
        self.assertIsNotNone(message.thread)
        self.assertIsNone(message.parent)

    def test_it_finds_the_recipient_regardless_of_email_case(self):
        # === Act ===
        response = self.client.post(
            self.url,
            data={
                'to': ['BOB@example.com'],
                'subject': 'Hello',
                'body': 'Hi there',
            },
            format='json',
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(MailboxEntry.objects.filter(user=self.bob, role=MailboxEntry.Role.TO).exists())

    def test_it_returns_the_senders_own_mailbox_entry(self):
        # === Act ===
        response = self.client.post(
            self.url,
            data={
                'to': ['bob@example.com'],
                'subject': 'Hello',
                'body': 'Hi there',
            },
            format='json',
        )

        # === Assert ===
        data = response.json()
        message = Message.objects.get()
        sender_entry = MailboxEntry.objects.get(message=message, user=self.alice)
        self.assertEqual(data['id'], sender_entry.pk)
        self.assertEqual(data['role'], MailboxEntry.Role.SENDER)
        self.assertTrue(data['is_read'])
        self.assertEqual(data['message']['subject'], 'Hello')
        self.assertEqual([lbl['name'] for lbl in data['labels']], ['sent'])

    def test_it_creates_entries_for_all_recipients_with_correct_role_and_labels(self):
        # === Act ===
        self.client.post(
            self.url,
            data={
                'to': ['bob@example.com'],
                'cc': ['carol@example.com'],
                'bcc': ['dave@example.com'],
                'subject': 'Hello',
                'body': 'Hi there',
            },
            format='json',
        )

        # === Assert ===
        message = Message.objects.get()
        self.assertEqual(MailboxEntry.objects.filter(message=message).count(), 4)

        bob_entry = MailboxEntry.objects.get(message=message, user=self.bob)
        self.assertEqual(bob_entry.role, MailboxEntry.Role.TO)
        self.assertFalse(bob_entry.is_read)
        self.assertTrue(bob_entry.labels.filter(name='inbox', is_system=True).exists())

        carol_entry = MailboxEntry.objects.get(message=message, user=self.carol)
        self.assertEqual(carol_entry.role, MailboxEntry.Role.CC)

        dave_entry = MailboxEntry.objects.get(message=message, user=self.dave)
        self.assertEqual(dave_entry.role, MailboxEntry.Role.BCC)

    def test_it_rejects_a_too_long_subject(self):
        # === Act ===
        response = self.client.post(
            self.url,
            data={
                'to': ['bob@example.com'],
                'subject': 'x' * 256,
                'body': 'Hi there',
            },
            format='json',
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'status': 400,
                'errors': [
                    {
                        'param': 'subject',
                        'message': 'Ensure this field has no more than 255 characters.',
                        'code': 'max_length',
                    }
                ],
            },
        )

    def test_it_returns_error_if_same_recipient_listed_twice(self):
        # === Act ===
        response = self.client.post(
            self.url,
            data={
                'to': ['bob@example.com'],
                'cc': ['BOB@example.com'],
                'subject': 's',
                'body': 'b',
            },
            format='json',
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'non_field_errors',
                        'message': 'The same recipient cannot be listed twice.',
                        'code': 'invalid',
                    }
                ],
                'status': 400,
            },
        )
        self.assertEqual(Message.objects.count(), 0)

    def test_it_returns_error_if_sending_to_self(self):
        # === Act ===
        response = self.client.post(
            self.url,
            data={
                'to': ['ALICE@example.com'],
                'subject': 's',
                'body': 'b',
            },
            format='json',
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'non_field_errors',
                        'message': 'You cannot add yourself as a recipient.',
                        'code': 'invalid',
                    }
                ],
                'status': 400,
            },
        )

    def test_it_returns_error_if_adding_yourself(self):
        # === Act ===
        response = self.client.post(
            self.url,
            data={
                'to': ['bob@example.com'],
                'cc': ['ALICE@example.com'],
                'subject': 's',
                'body': 'b',
            },
            format='json',
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'non_field_errors',
                        'message': 'You cannot add yourself as a recipient.',
                        'code': 'invalid',
                    }
                ],
                'status': 400,
            },
        )

    def test_it_returns_error_for_unknown_recipient(self):
        # === Act ===
        response = self.client.post(
            self.url,
            data={
                'to': ['ghost@example.com'],
                'subject': 's',
                'body': 'b',
            },
            format='json',
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'non_field_errors',
                        'message': 'Unknown recipients: ghost@example.com',
                        'code': 'invalid',
                    }
                ],
                'status': 400,
            },
        )
        self.assertEqual(Message.objects.count(), 0)

    def test_it_returns_error_if_to_missing(self):
        # === Act ===
        response = self.client.post(self.url, data={'subject': 's', 'body': 'b'}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [{'param': 'to', 'message': 'This field is required.', 'code': 'required'}],
                'status': 400,
            },
        )

    def test_it_returns_error_if_body_missing(self):
        # === Act ===
        response = self.client.post(self.url, data={'to': ['bob@example.com'], 'subject': 's'}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [{'param': 'body', 'message': 'This field is required.', 'code': 'required'}],
                'status': 400,
            },
        )

    def test_it_allows_blank_subject(self):
        # === Act ===
        response = self.client.post(
            self.url, data={'to': ['bob@example.com'], 'subject': '', 'body': 'b'}, format='json'
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = Message.objects.get()
        self.assertEqual(message.subject, '')

    def test_it_not_allows_blank_body(self):
        # === Act ===
        response = self.client.post(
            self.url, data={'to': ['bob@example.com'], 'subject': 's', 'body': ''}, format='json'
        )

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {'status': 400, 'errors': [{'param': 'body', 'message': 'This field may not be blank.', 'code': 'blank'}]},
        )

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()

        # === Act ===
        response = self.client.post(self.url, data={'to': ['bob@example.com']}, format='json')

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

        # === Act ===
        for _ in range(3):
            response = self.client.post(
                self.url,
                data={
                    'to': ['bob@example.com'],
                    'cc': ['carol@example.com'],
                    'bcc': ['dave@example.com'],
                    'subject': 'Hello',
                    'body': 'Hi there',
                },
                format='json',
            )

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
        # === Act ===
        for _ in range(3):
            response = self.client.post(self.url, data={'subject': 's', 'body': 'b'}, format='json')

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
