from django.contrib import admin
from .models import (
    Category, ItemType, FavoriteCategory, Item, ItemImage,
    SearchHistory, ViewHistory, Transaction, Review
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(ItemType)
class ItemTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('name',)

@admin.register(FavoriteCategory)
class FavoriteCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'category', 'created_at')
    list_filter = ('user', 'category')
    search_fields = ('user__username', 'category__name')

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'owner', 'price', 'status', 'created_at')
    list_filter = ('status', 'type__category', 'owner')
    search_fields = ('name', 'description', 'owner__username')
    raw_id_fields = ('owner', 'type')

@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'is_main', 'alt_text')
    list_filter = ('is_main', 'item__type__category')
    search_fields = ('item__name', 'alt_text')

@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'query_text', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('query_text', 'user__username')

@admin.register(ViewHistory)
class ViewHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'item', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('user__username', 'item__name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'owner', 'renter', 'is_active', 'rented_at', 'returned_at', 'created_at')
    list_filter = ('is_active', 'rented_at', 'returned_at') 
    search_fields = ('item__name', 'owner__username', 'renter__username')
    raw_id_fields = ('owner', 'renter', 'item')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'author', 'transaction', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'author__username', 'item__name')