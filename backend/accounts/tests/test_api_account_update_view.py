from django.contrib.auth import get_user_model
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class APIAccountUpdateViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'Sup3r-Str0ng-Pa55word'
        cls.user = User.objects.create_user(
            email='john@example.com', password=cls.password, first_name='John', last_name='Doe'
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('accounts:account-me')

    def test_it_partially_updates_account(self):
        # === Arrange ===
        data = {'first_name': 'Jane', 'current_password': self.password}

        # === Act ===
        response = self.client.patch(self.url, data=data)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')
        self.assertEqual(self.user.last_name, 'Doe')

    def test_it_fully_updates_account(self):
        # === Arrange ===
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com',
            'current_password': self.password,
        }

        # === Act ===
        response = self.client.put(self.url, data=data)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')
        self.assertEqual(self.user.last_name, 'Smith')
        self.assertEqual(self.user.email, 'jane@example.com')

    def test_it_returns_error_if_current_password_is_incorrect(self):
        # === Arrange ===
        data = {'first_name': 'Jane', 'current_password': 'wrong-password'}

        # === Act ===
        response = self.client.patch(self.url, data=data)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'current_password',
                        'message': 'Incorrect current password',
                        'code': 'invalid',
                    }
                ],
                'status': 400,
            },
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')

    def test_it_returns_error_if_current_password_missing(self):
        # === Arrange ===
        data = {'first_name': 'Jane'}

        # === Act ===
        response = self.client.patch(self.url, data=data)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'current_password',
                        'message': 'This field is required.',
                        'code': 'required',
                    }
                ],
                'status': 400,
            },
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')

    def test_it_returns_error_if_email_already_exists(self):
        # === Arrange ===
        data = {'email': G(User).email, 'current_password': self.password}

        # === Act ===
        response = self.client.patch(self.url, data=data)

        # === Assert ===
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                'errors': [
                    {
                        'param': 'email',
                        'message': 'user with this email already exists.',
                        'code': 'unique',
                    }
                ],
                'status': 400,
            },
        )

    def test_it_returns_error_if_required_field_missing_on_put(self):
        for field in ('first_name', 'last_name', 'email'):
            with self.subTest(field=field):
                # === Arrange ===
                data = {
                    'first_name': 'Jane',
                    'last_name': 'Smith',
                    'email': 'jane@example.com',
                    'current_password': self.password,
                }
                del data[field]

                # === Act ===
                response = self.client.put(self.url, data=data)

                # === Assert ===
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    response.json(),
                    {
                        'errors': [
                            {
                                'param': field,
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
        data = {'first_name': 'Jane', 'current_password': self.password}

        # === Act ===
        response = self.client.patch(self.url, data=data)

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
