from django.db import models
from users.models import User
from listings.models import Item

class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "pending" # запрос на совладение/аренду
        APPROVED = "approved", "approved" # запрос подтвердили
        ACTIVE = "active", "active" # сделка активна
        RETURNING = "returning", "returning" # в процессе возврата
        COMPLETED = "completed", "completed" # сделка завершена

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', blank=True)
    renter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rented_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='transactions')
    # inspection_checklist = models.JSONField(default=dict, blank=True)
    rented_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING)
    returned_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.owner_id:
            self.owner = self.item.owner
        super().save(*args, **kwargs)
