from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User

class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ['email', 'username',]
    # todo: дописать админку

admin.site.register(User, UserAdmin)