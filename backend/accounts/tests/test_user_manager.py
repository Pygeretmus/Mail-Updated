from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django_dynamic_fixture import G

from mail.constants import SYSTEM_LABELS

User = get_user_model()


class UserManagerCreateUserTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.email = 'john@example.com'
        cls.password = 'Sup3r-Str0ng-Pa55word'
        cls.first_name = 'John'
        cls.last_name = 'Doe'

    def test_it_creates_user(self):
        # === Act ===
        user = User.objects.create_user(
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

        # === Assert ===
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertEqual(user.email, self.email)
        self.assertEqual(user.first_name, self.first_name)
        self.assertEqual(user.last_name, self.last_name)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_it_creates_system_labels(self):
        # === Act ===
        user = User.objects.create_user(
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

        # === Assert ===
        self.assertFalse(user.labels.filter(is_system=False).exists())
        self.assertEqual(
            set(user.labels.filter(is_system=True).values_list('name', flat=True)),
            set(SYSTEM_LABELS),
        )

    def test_it_hashes_password(self):
        # === Act ===
        user = User.objects.create_user(email=self.email, password=self.password)

        # === Assert ===
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))

    def test_it_sets_unusable_password_if_password_not_passed(self):
        # === Act ===
        user = User.objects.create_user(email=self.email)

        # === Assert ===
        self.assertFalse(user.has_usable_password())

    def test_it_normalizes_email_domain(self):
        # === Act ===
        user = User.objects.create_user(email='john@EXAMPLE.COM', password=self.password)

        # === Assert ===
        self.assertEqual(user.email, self.email)

    def test_it_does_not_override_passed_extra_fields(self):
        # === Act ===
        user = User.objects.create_user(email=self.email, password=self.password, is_staff=True)

        # === Assert ===
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_it_raises_error_if_email_is_none(self):
        # === Act & Assert ===
        with self.assertRaisesMessage(ValueError, 'The given email must be set'):
            User.objects.create_user(email=None, password=self.password)
        self.assertEqual(User.objects.count(), 0)

    def test_it_raises_error_if_email_is_empty(self):
        # === Act & Assert ===
        with self.assertRaisesMessage(ValueError, 'The given email must be set'):
            User.objects.create_user(email='', password=self.password)
        self.assertEqual(User.objects.count(), 0)

    def test_it_raises_error_if_email_already_exists(self):
        # === Arrange ===
        G(User, email=self.email)

        # === Act & Assert ===
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email=self.email, password=self.password)
        self.assertEqual(User.objects.count(), 1)


class UserManagerCreateSuperuserTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.email = 'admin@example.com'
        cls.password = 'Sup3r-Str0ng-Pa55word'
        cls.first_name = 'John'
        cls.last_name = 'Doe'

    def test_it_creates_superuser(self):
        # === Act ===
        user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

        # === Assert ===
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(self.password))

    def test_it_creates_system_labels(self):
        # === Act ===
        user = User.objects.create_superuser(
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

        # === Assert ===
        self.assertFalse(user.labels.filter(is_system=False).exists())
        self.assertEqual(
            set(user.labels.filter(is_system=True).values_list('name', flat=True)),
            set(SYSTEM_LABELS),
        )

    def test_it_hashes_password(self):
        # === Act ===
        user = User.objects.create_superuser(email=self.email, password=self.password)

        # === Assert ===
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))

    def test_it_sets_unusable_password_if_password_not_passed(self):
        # === Act ===
        user = User.objects.create_superuser(email=self.email)

        # === Assert ===
        self.assertFalse(user.has_usable_password())

    def test_it_normalizes_email_domain(self):
        # === Act ===
        user = User.objects.create_superuser(email='admin@EXAMPLE.COM', password=self.password)

        # === Assert ===
        self.assertEqual(user.email, self.email)

    def test_it_raises_error_if_is_staff_false(self):
        # === Act & Assert ===
        with self.assertRaisesMessage(ValueError, 'Superuser must have is_staff=True.'):
            User.objects.create_superuser(
                email=self.email,
                password=self.password,
                first_name=self.first_name,
                last_name=self.last_name,
                is_staff=False,
            )
        self.assertEqual(User.objects.count(), 0)

    def test_it_raises_error_if_is_superuser_false(self):
        # === Act & Assert ===
        with self.assertRaisesMessage(ValueError, 'Superuser must have is_superuser=True.'):
            User.objects.create_superuser(
                email=self.email,
                password=self.password,
                first_name=self.first_name,
                last_name=self.last_name,
                is_superuser=False,
            )
        self.assertEqual(User.objects.count(), 0)

    def test_it_raises_error_if_email_is_none(self):
        # === Act & Assert ===
        with self.assertRaisesMessage(ValueError, 'The given email must be set'):
            User.objects.create_superuser(email=None, password=self.password)
        self.assertEqual(User.objects.count(), 0)

    def test_it_raises_error_if_email_is_empty(self):
        # === Act & Assert ===
        with self.assertRaisesMessage(ValueError, 'The given email must be set'):
            User.objects.create_superuser(
                email='', password=self.password, first_name=self.first_name, last_name=self.last_name
            )

    def test_it_raises_error_if_email_already_exists(self):
        # === Arrange ===
        G(User, email=self.email)

        # === Act & Assert ===
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_superuser(email=self.email, password=self.password)
        self.assertEqual(User.objects.count(), 1)
