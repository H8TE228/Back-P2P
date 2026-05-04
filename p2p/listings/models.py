from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']


class ItemType(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='types')
    name = models.CharField(max_length=100)
    usage_tips = models.TextField(blank=True, null=True)
    safety_rules = models.TextField(blank=True, null=True)
    inspection_checklist = models.JSONField(default=dict, blank=True)
    characteristics_template = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        verbose_name = "Тип предмета"
        verbose_name_plural = "Типы предметов"
        unique_together = ['category', 'name']


class FavoriteCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_categories_rel')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.category.name}"

    class Meta:
        verbose_name = "Избранная категория"
        verbose_name_plural = "Избранные категории"
        unique_together = ['user', 'category']


class Item(models.Model):
    class DeliveryMethods(models.TextChoices):
        PICKUP = "pickup", "pickup"
        MAIL = "mail", "mail"

    STATUS_CHOICES = [
        ('available', 'Доступен'),
        ('rented', 'Сдан'),
        ('maintenance', 'На обслуживании'),
        ('unavailable', 'Недоступен'),
    ]

    type = models.ForeignKey(ItemType, on_delete=models.CASCADE, related_name='items')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_items')
    name = models.CharField(max_length=200)
    description = models.TextField()
    characteristics = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    avaliability_calendar = models.JSONField(default=list, blank=True)
    delivery_method = models.CharField(max_length=6, choices=DeliveryMethods, default=DeliveryMethods.PICKUP, blank=True)
    max_active_transactions = models.IntegerField(default=1, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    @property
    def main_image_obj(self):
        for img in self.images.all():
            if img.is_main:
                return img
        return None

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"
        ordering = ['-created_at']


class ItemImage(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='items/%Y/%m/%d/', help_text="Изображение предмета")
    alt_text = models.CharField(max_length=200, blank=True, null=True)
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.item.name}"

    class Meta:
        verbose_name = "Изображение предмета"
        verbose_name_plural = "Изображения предметов"
        ordering = ['-is_main', 'created_at']


class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    query_text = models.CharField(max_length=255, blank=True, default='')
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_searched_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        text = self.query_text or '<без текста>'
        return f"{self.user.username}: {text[:30]}"

    class Meta:
        verbose_name = "История поиска"
        verbose_name_plural = "Истории поиска"
        ordering = ['-last_searched_at']


class ViewHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='view_history')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='viewers')
    created_at = models.DateTimeField(auto_now_add=True)
    last_viewed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} viewed {self.item.name}"

    class Meta:
        verbose_name = "История просмотра"
        verbose_name_plural = "Истории просмотров"
        ordering = ['-last_viewed_at']
        unique_together = ['user', 'item']


class Review(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
    transaction = models.ForeignKey('transactions.Transaction', on_delete=models.CASCADE, related_name='reviews')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='reviews')

    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.author.username} for {self.recipient.username} (item: {self.item.name})"

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']
        unique_together = ['author', 'transaction']


class FavoriteItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_items_rel')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ❤ {self.item.name}"

    class Meta:
        verbose_name = "Избранный предмет"
        verbose_name_plural = "Избранные предметы"
        ordering = ['-created_at']
        unique_together = ['user', 'item']


class Notification(models.Model):
    """
    Минимальная модель уведомлений для MVP.
    Создаётся бэкендом, потребляется фронтом через polling.
    Push/email/websocket-доставка — за рамками MVP.
    """
    class Kind(models.TextChoices):
        FAVORITE_ITEM_AVAILABLE = "favorite_available", "Избранный предмет освободился"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=32, choices=Kind.choices)
    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name='notifications',
        null=True, blank=True,
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.kind}] {self.user.username}: {self.message[:40]}"

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']