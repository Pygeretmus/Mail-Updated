from django.contrib.auth import get_user_model
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Label

User = get_user_model()


class APILabelDestroyViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = G(User)
        cls.other_user = G(User)
        cls.label = G(Label, user=cls.user, name='Custom', is_system=False)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('mail:label-detail', args=[self.label.pk])

    def test_it_destroys_custom_label(self):
        # === Act ===
        response = self.client.delete(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Label.objects.filter(pk=self.label.pk).exists())

    def test_it_returns_error_if_label_is_system(self):
        # === Arrange ===
        self.label.is_system = True
        self.label.save(update_fields=['is_system'])

        # === Act ===
        response = self.client.delete(self.url)

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
        self.assertTrue(Label.objects.filter(pk=self.label.pk).exists())

    def test_it_returns_error_if_label_belongs_to_another_user(self):
        # === Arrange ===
        self.label.user = self.other_user
        self.label.save(update_fields=['user'])

        # === Act ===
        response = self.client.delete(self.url)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Label.objects.filter(pk=self.label.pk).exists())

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
