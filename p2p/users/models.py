from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    # username, first_name, last_name
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(_('phone number'), max_length=20, blank=True)
    profile_picture = models.ImageField(_('profile picture'), upload_to='pfp/', blank=True, null=True)
    
    country = models.CharField(_('country'), max_length=256)
    region = models.CharField(_('region'), max_length=256)
    city = models.CharField(_('city'), max_length=256)
    district = models.CharField(_('district'), max_length=256)
    street = models.CharField(_('street'), max_length=256)
    building = models.CharField(_('building'), max_length=256)
    apartment = models.CharField(_('apartment'), max_length=256)

    created_at = models.DateField(_('creation date'), auto_now_add=True)
    updated_at = models.DateField(_('last update date'), auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
