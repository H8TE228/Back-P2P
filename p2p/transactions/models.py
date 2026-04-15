from django.db import models
from users.models import User
from listings.models import Listing

class Transaction(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', blank=True)
    renter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rented_items')
    item = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='transactions')
    # inspection_checklist = models.JSONField(default=dict, blank=True)
    rented_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    returned_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.owner_id:
            self.owner = self.item.owner
        super().save(*args, **kwargs)
