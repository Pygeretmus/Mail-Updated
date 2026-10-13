from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Label, MailboxEntry, Message

User = get_user_model()


class APIMailboxListViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.other_user = G(User)

    def _build_expected_mailbox_response(self, entries: list[MailboxEntry]):
        result = []
        for entry in entries:
            message = entry.message

            result.append(
                {
                    'id': entry.pk,
                    'message': {
                        'id': message.pk,
                        'thread': message.thread.pk,
                        'sender': message.sender.email,
                        'subject': message.subject,
                        'created_at': message.created_at.isoformat().replace('+00:00', 'Z'),
                    },
                    'role': entry.role,
                    'is_read': entry.is_read,
                    'deleted_at': entry.deleted_at.isoformat().replace('+00:00', 'Z') if entry.deleted_at else None,
                    'labels': [
                        {'id': label.id, 'is_system': label.is_system, 'name': label.name}
                        for label in entry.labels.all()
                    ],
                }
            )

        return result

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:mailbox-list')

    def test_it_returns_only_own_entries(self):
        # === Arrange ===
        own_entry = G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))
        G(MailboxEntry, user=self.other_user, message=G(Message, sender=G(User)))

        # === Act ===
        response = self.client.get(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'], self._build_expected_mailbox_response([own_entry]))

    def test_it_orders_by_newest_message_first(self):
        # === Arrange ===
        older = G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))
        newer = G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))

        # === Act ===
        response = self.client.get(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'], self._build_expected_mailbox_response([newer, older]))

    def test_it_returns_paginated_list(self):
        # === Arrange ===
        older = G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))
        newer = G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))

        # === Act ===
        first_response = self.client.get(self.url + '?page_size=1&page=1')
        second_response = self.client.get(self.url + '?page_size=1&page=2')

        # === Assert ===
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.json()['results'], self._build_expected_mailbox_response([newer]))
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.json()['results'], self._build_expected_mailbox_response([older]))

    def test_it_excludes_deleted(self):
        # === Arrange ===
        G(MailboxEntry, user=self.user, deleted_at=timezone.now(), message=G(Message, sender=G(User)))
        kept = G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))

        # === Act ===
        response = self.client.get(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'], self._build_expected_mailbox_response([kept]))

    def test_it_filters_by_system_label(self):
        # === Arrange ===
        system_label = G(Label, user=self.user, is_system=True)
        matching = G(MailboxEntry, user=self.user, labels=[system_label], message=G(Message, sender=G(User)))
        G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))

        # === Act ===
        response = self.client.get(self.url, {'label': system_label.name})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'], self._build_expected_mailbox_response([matching]))

    def test_it_filters_by_custom_label_case_insensitively(self):
        # === Arrange ===
        important = G(Label, user=self.user, name='Important', is_system=False)
        matching = G(MailboxEntry, user=self.user, labels=[important], message=G(Message, sender=G(User)))
        G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))

        # === Act ===
        response = self.client.get(self.url, {'label': 'important'})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'], self._build_expected_mailbox_response([matching]))

    def test_deleted_true_ignores_label_filter(self):
        # === Arrange ===
        deleted = G(MailboxEntry, user=self.user, deleted_at=timezone.now(), message=G(Message, sender=G(User)))
        G(MailboxEntry, user=self.user, message=G(Message, sender=G(User)))  # not deleted, must not match

        # === Act ===
        response = self.client.get(self.url, {'deleted': 'true', 'label': 'inbox'})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['results'], self._build_expected_mailbox_response([deleted]))

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
