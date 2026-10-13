from django.contrib.auth import get_user_model
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Label

User = get_user_model()


class APILabelUpdateViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.other_user = G(User)
        cls.label = G(Label, user=cls.user, name='Old name', is_system=False)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:label-detail', args=[self.label.pk])

    def test_it_updates_custom_label(self):
        # === Act ===
        response = self.client.patch(self.url, data={'name': 'New name'})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.label.refresh_from_db()
        self.assertEqual(self.label.name, 'New name')

    def test_it_allows_keeping_the_same_name(self):
        # === Act ===
        response = self.client.patch(self.url, data={'name': 'Old name'})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_it_returns_error_if_label_is_system(self):
        # === Arrange ===
        self.label.is_system = True
        self.label.save(update_fields=['is_system'])

        # === Act ===
        response = self.client.patch(self.url, data={'name': 'New name'})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': None,
                        'message': "System labels can't be changed",
                        'code': 'permission_denied',
                    }
                ],
                'status': 403,
            },
        )
        self.label.refresh_from_db()
        self.assertEqual(self.label.name, 'Old name')

    def test_it_returns_error_if_name_already_exists(self):
        # === Arrange ===
        G(Label, user=self.user, name='Taken', is_system=False)

        # === Act ===
        response = self.client.patch(self.url, data={'name': 'Taken'})

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

    def test_it_returns_error_if_name_reserved(self):
        # === Act ===
        response = self.client.patch(self.url, data={'name': 'trash'})

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
        G(Label, user=self.other_user, name='Taken', is_system=False)

        # === Act ===
        response = self.client.patch(self.url, data={'name': 'Taken'})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.label.refresh_from_db()
        self.assertEqual(self.label.name, 'Taken')

    def test_it_returns_error_if_label_belongs_to_another_user(self):
        # === Arrange ===
        self.label.user = self.other_user
        self.label.save(update_fields=['user'])

        # === Act ===
        response = self.client.patch(self.url, data={'name': 'New name'})

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.label.name, 'Old name')

    def test_it_returns_error_if_not_authenticated(self):
        # === Arrange ===
        self.client.logout()

        # === Act ===
        response = self.client.patch(self.url, data={'name': 'New name'})

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
