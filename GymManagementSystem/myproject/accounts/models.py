from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        TRAINER = 'trainer', 'Trainer'
        MEMBER = 'member', 'Member'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    phone = models.CharField(max_length=15, blank=True)

    @property
    def is_member(self):
        return self.role == self.Role.MEMBER

    @property
    def is_trainer(self):
        return self.role == self.Role.TRAINER
