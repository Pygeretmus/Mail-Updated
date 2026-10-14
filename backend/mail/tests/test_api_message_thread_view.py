from django.contrib.auth import get_user_model
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from ..services import send_message

User = get_user_model()


class APIMessageThreadViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = G(User, email='alice@example.com')
        cls.bob = G(User, email='bob@example.com')
        cls.stranger = G(User, email='stranger@example.com')

    def setUp(self):
        self.client.force_authenticate(user=self.alice)
        original = send_message(
            sender=self.alice,
            subject='Hi',
            body='b',
            recipients={'to': [self.bob]},
        )
        self.original_message_id = original.pk
        self.thread_id = original.thread_id

        send_message(
            sender=self.bob,
            subject='Re: Hi',
            body='reply',
            recipients={'to': [self.alice]},
            thread=original.thread,
            parent=original,
        )

    def test_it_returns_messages_ordered_by_creation(self):
        # === Arrange ===
        url = reverse('mail:message-thread', args=[self.thread_id])

        # === Act ===
        response = self.client.get(url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subjects = [entry['message']['subject'] for entry in response.json()]
        self.assertEqual(subjects, ['Hi', 'Re: Hi'])

    def test_it_returns_only_the_requesting_users_own_entries(self):
        # === Arrange ===
        url = reverse('mail:message-thread', args=[self.thread_id])

        # === Act: alice's view ===
        alice_response = self.client.get(url)

        # === Act: bob's view ===
        self.client.force_authenticate(self.bob)
        bob_response = self.client.get(url)

        # === Assert ===
        alice_roles = [entry['role'] for entry in alice_response.json()]
        bob_roles = [entry['role'] for entry in bob_response.json()]
        self.assertEqual(alice_roles, ['sender', 'to'])
        self.assertEqual(bob_roles, ['to', 'sender'])

    def test_it_reflects_each_users_own_read_state(self):
        # Bob hasn't opened Alice's original message yet, so his entry
        # for it should still be unread, independent of Alice's.
        # === Arrange ===
        url = reverse('mail:message-thread', args=[self.thread_id])
        self.client.force_authenticate(self.bob)

        # === Act ===
        response = self.client.get(url)

        # === Assert ===
        original_entry = next(e for e in response.json() if e['message']['subject'] == 'Hi')
        self.assertFalse(original_entry['is_read'])

    def test_it_returns_empty_list_for_a_thread_the_user_does_not_participate_in(self):
        # === Arrange ===
        self.client.force_authenticate(self.stranger)
        url = reverse('mail:message-thread', args=[self.thread_id])

        # === Act ===
        response = self.client.get(url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_it_returns_empty_list_for_unknown_thread(self):
        # === Act ===
        response = self.client.get(reverse('mail:message-thread', args=[999999]))

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()
        url = reverse('mail:message-thread', args=[self.thread_id])

        # === Act ===
        response = self.client.get(url)

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
