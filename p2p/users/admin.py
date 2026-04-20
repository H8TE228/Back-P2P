from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User

class UserAdmin(BaseUserAdmin):
    model = User
    readonly_fields = ['last_login', 'created_at', 'updated_at', 'rating_display']
    list_display = [
        'email',
        'username',
        'phone_number',
        'country',
        'region',
        'city',
        'district',
        'rating_display',
        'created_at',
        'updated_at'
    ]
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number', 'profile_picture')}),
        (_('Address'), {'fields': ('country', 'region', 'city', 'district', 'street', 'building', 'apartment')}),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at', 'rating_display')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'phone_number', 'password1', 'password2', 'is_staff'),
        }),
    )
    list_filter = ['country', 'region', 'city', 'district', 'created_at', 'updated_at']
    search_fields = ['email', 'username', 'phone_number']
    ordering = ['email',]

    def rating_display(self, obj):
        from listings.models import Review
        from django.db.models import Avg
        avg_rating = Review.objects.filter(recipient=obj).aggregate(avg=Avg('rating'))['avg']
        if avg_rating:
            return f"{avg_rating:.2f}"
        return "Нет оценок"
    rating_display.short_description = 'Рейтинг'

admin.site.register(User, UserAdmin)