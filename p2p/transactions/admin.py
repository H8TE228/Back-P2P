from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html


from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'owner', 'renter', 'status_colored', 'rented_at', 'returned_at')
    list_filter = ('status', 'rented_at', 'owner')
    search_fields = ('item__name', 'owner__username', 'renter__username')
    readonly_fields = ('rented_at', 'returned_at', 'owner')

    fieldsets = (
        (_('Participants of transaction'), {'fields': ('owner', 'renter', 'item')}),
        (_('Status and time'), {'fields': ('status', 'rented_at', 'returned_at')}),
    )

    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'active': 'green',
            'rejected': 'red',
            'returning': 'orange',
            'completed': 'blue',
        }
        return format_html(
            '<b style="color: {};">{}</b>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
