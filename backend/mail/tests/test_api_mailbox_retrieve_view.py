from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from mail.models import MailboxEntry, Message

User = get_user_model()


class APIMailboxRetrieveViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.other_user = G(User)
        cls.entry = G(MailboxEntry, user=cls.user, message=G(Message, sender=G(User)))

    def _build_expected_mailbox_response(self, entry: MailboxEntry):
        message = entry.message

        return {
            'id': entry.pk,
            'message': {
                'id': message.pk,
                'thread': message.thread.pk,
                'parent': None,
                'sender': message.sender.email,
                'subject': message.subject,
                'body': message.body,
                'created_at': message.created_at.isoformat().replace('+00:00', 'Z'),
                'recipients': [],
            },
            'role': entry.role,
            'is_read': entry.is_read,
            'deleted_at': entry.deleted_at.isoformat().replace('+00:00', 'Z') if entry.deleted_at else None,
            'labels': [
                {'id': label.id, 'is_system': label.is_system, 'name': label.name} for label in entry.labels.all()
            ],
        }

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:mailbox-detail', args=[self.entry.pk])

    def test_it_returns_only_own_entries(self):
        # === Act ===
        response = self.client.get(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), self._build_expected_mailbox_response(self.entry))

    def test_it_shows_soft_deleted(self):
        # === Arrange ===
        self.entry.deleted_at = timezone.now()
        self.entry.save(update_fields=['deleted_at'])

        # === Act ===
        response = self.client.get(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), self._build_expected_mailbox_response(self.entry))

    def test_it_returns_error_if_entry_belongs_to_another_user(self):
        # === Arrange ===
        self.entry.user = self.other_user
        self.entry.save(update_fields=['user'])

        # === Act ===
        response = self.client.get(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()

        # === Act ===
        response = self.client.get(self.url)

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
