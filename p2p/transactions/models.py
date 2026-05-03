from django.db import models, transaction
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from users.models import User
from listings.models import Item


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "pending" # запрос на совладение/аренду
        APPROVED = "approved", "approved" # запрос подтвердили
        REJECTED = "rejected", "rejected" # запрос отклонили
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

        if self.status == self.Status.COMPLETED and not self.returned_at:
            self.returned_at = timezone.now()
        super().save(*args, **kwargs)

    def change_status(self, new_status):
        status_check = [
            self.Status.PENDING,
            self.Status.APPROVED,
        ]
        active_transaction = [
            self.Status.APPROVED, 
            self.Status.ACTIVE, 
            self.Status.RETURNING,
        ]
        with transaction.atomic():
            if new_status in status_check:
                item = Item.objects.select_for_update().get(pk=self.item_id)
                active_count = item.transactions.filter(
                    status__in=active_transaction
                ).exclude(pk=self.pk).count()
                
                if active_count >= item.max_active_transactions:
                    raise ValidationError(f"Лимит активных транзакций ({item.max_active_transactions}) исчерпан.")
                
            self.status = new_status
            self.save()