from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from mail.models import MailboxEntry

User = get_user_model()


class APIMailboxEraseEntryViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.other_user = G(User)
        cls.entry = G(MailboxEntry, user=cls.user, deleted_at=timezone.now())

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:mailbox-erase-entry', args=[self.entry.pk])

    def test_it_erases_deleted_entry(self):
        # === Act ===
        response = self.client.delete(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MailboxEntry.objects.filter(pk=self.entry.pk).exists())

    def test_it_returns_error_if_entry_is_not_in_trash(self):
        # === Arrange ===
        self.entry.deleted_at = None
        self.entry.save(update_fields=['deleted_at'])

        # === Act ===
        response = self.client.delete(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(MailboxEntry.objects.filter(pk=self.entry.pk).exists())

    def test_it_returns_error_if_entry_belongs_to_another_user(self):
        # === Arrange ===
        self.entry.user = self.other_user
        self.entry.save(update_fields=['user'])

        # === Act ===
        response = self.client.delete(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(MailboxEntry.objects.filter(pk=self.entry.pk).exists())

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()

        # === Act ===
        response = self.client.delete(self.url)

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
