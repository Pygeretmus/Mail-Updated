from django.contrib.auth import get_user_model
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from ..constants import SYSTEM_LABELS
from ..models import Label

User = get_user_model()


class APILabelListViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.other_user = G(User)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:label-list')

    def test_it_returns_own_labels_ordered_by_name(self):
        # === Arrange ===
        G(Label, user=self.user, name='Zeta', is_system=False)
        G(Label, user=self.user, name='Alpha', is_system=False)

        # === Act ===
        response = self.client.get(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([label['name'] for label in response.json()], SYSTEM_LABELS + ['Zeta', 'Alpha'])

    def test_it_does_not_return_other_users_labels(self):
        # === Arrange ===
        G(Label, user=self.other_user, name='Secret', is_system=False)

        # === Act ===
        response = self.client.get(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([label['name'] for label in response.json()], SYSTEM_LABELS)

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
