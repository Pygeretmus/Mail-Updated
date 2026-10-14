from django.contrib.auth import get_user_model
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from mail.models import Label, MailboxEntry

User = get_user_model()


class APIMailboxUpdateStateViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.other_user = G(User)
        cls.entry = G(MailboxEntry, user=cls.user)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:mailbox-update-state', args=[self.entry.pk])

    def test_it_marks_as_read(self):
        # === Act ===
        response = self.client.patch(self.url, data={'is_read': True}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.entry.refresh_from_db()
        self.assertTrue(self.entry.is_read)

    def test_it_sets_labels(self):
        # === Arrange ===
        label = G(Label, user=self.user, name='Important', is_system=False)

        # === Act ===
        response = self.client.patch(self.url, data={'label_ids': [label.pk]}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(self.entry.labels.values_list('pk', flat=True)), [label.pk])

    def test_it_returns_error_if_label_belongs_to_another_user(self):
        # === Arrange ===
        foreign_label = G(Label, user=self.other_user, name='Not yours', is_system=False)

        # === Act ===
        response = self.client.patch(self.url, data={'label_ids': [foreign_label.pk]}, format='json')

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.entry.labels.count(), 0)

    def test_it_returns_error_if_entry_belongs_to_another_user(self):
        # === Arrange ===
        self.entry.user = self.other_user
        self.entry.save(update_fields=['user'])

        # === Act ===
        response = self.client.patch(self.url, data={'is_read': True})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()

        # === Act ===
        response = self.client.patch(self.url, data={'is_read': True})

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
