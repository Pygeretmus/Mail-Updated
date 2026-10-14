from django.contrib.auth import get_user_model
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from mail.models import Label, MailboxEntry

User = get_user_model()


class APIMailboxDeleteEntryViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.other_user = G(User)
        cls.entry = G(MailboxEntry, user=cls.user, deleted_at=None)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:mailbox-delete-entry', args=[self.entry.pk])

    def test_it_soft_deletes_entry(self):
        # === Act ===
        response = self.client.post(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.entry.refresh_from_db()
        self.assertIsNotNone(self.entry.deleted_at)

    def test_it_keeps_labels(self):
        # === Arrange ===
        label = G(Label, user=self.user, name='Important', is_system=False)
        self.entry.labels.add(label)

        # === Act ===
        response = self.client.post(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(list(self.entry.labels.values_list('pk', flat=True)), [label.pk])

    def test_it_returns_error_if_entry_belongs_to_another_user(self):
        # === Arrange ===
        self.entry.user = self.other_user
        self.entry.save(update_fields=['user'])

        # === Act ===
        response = self.client.post(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.deleted_at)

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()

        # === Act ===
        response = self.client.post(self.url)

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
