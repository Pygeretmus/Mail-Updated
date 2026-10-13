from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)

    USERNAME_FIELD = 'email'
    # The 'USERNAME_FIELD' must not be included in 'REQUIRED_FIELDS'
    REQUIRED_FIELDS: ClassVar[list[str]] = ['first_name', 'last_name']

    objects = UserManager()

    def save(self, *args, **kwargs):
        is_created = self._state.adding

        with transaction.atomic():
            super().save(*args, **kwargs)

            if is_created:
                from mail.constants import SYSTEM_LABELS
                from mail.models import Label

                Label.objects.bulk_create(
                    [Label(user=self, name=name, is_system=True) for name in SYSTEM_LABELS],
                    ignore_conflicts=True,
                )

    def __str__(self):
        return self.email

    class Meta(AbstractUser.Meta):
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(Lower('email'), name='uniq_user_email_ci')
        ]
