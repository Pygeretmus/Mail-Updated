from django.contrib.auth import get_user_model
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from ..constants import SYSTEM_LABELS
from ..models import Label

User = get_user_model()


class APILabelCreateViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.label_name = 'Urgent'

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:label-list')

    def test_it_creates_label(self):
        # === Act ===
        response = self.client.post(self.url, data={'name': self.label_name})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Label.objects.count(), 1 + len(SYSTEM_LABELS))
        label = Label.objects.get(name=self.label_name)
        self.assertEqual(label.user, self.user)
        self.assertFalse(label.is_system)

    def test_it_returns_error_if_name_already_exists(self):
        # === Arrange ===
        G(Label, user=self.user, name=self.label_name)

        # === Act ===
        response = self.client.post(self.url, data={'name': self.label_name})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'name',
                        'message': 'Label with this name already exists.',
                        'code': 'invalid',
                    }
                ],
                'status': 400,
            },
        )
        self.assertEqual(Label.objects.count(), 1 + len(SYSTEM_LABELS))

    def test_it_returns_error_if_name_reserved(self):
        # === Act ===
        response = self.client.post(self.url, data={'name': 'trash'})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'name',
                        'message': 'This label name is reserved.',
                        'code': 'invalid',
                    }
                ],
                'status': 400,
            },
        )

    def test_it_allows_same_name_for_different_users(self):
        # === Arrange ===
        other_user = G(User)
        G(Label, user=other_user, name=self.label_name)

        # === Act ===
        response = self.client.post(self.url, data={'name': self.label_name})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Label.objects.filter(name=self.label_name).count(), 2)

    def test_it_returns_error_if_name_missing(self):
        # === Act ===
        response = self.client.post(self.url, data={})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'name',
                        'message': 'This field is required.',
                        'code': 'required',
                    }
                ],
                'status': 400,
            },
        )

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()

        # === Act ===
        response = self.client.post(self.url, data={'name': 'Urgent'})

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
