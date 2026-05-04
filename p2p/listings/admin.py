from django.contrib import admin
from .models import (
    Category, ItemType, Notification, FavoriteCategory, FavoriteItem, Item, ItemImage,
    SearchHistory, ViewHistory, Review
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
    list_display = ('id', 'user', 'query_text', 'filters', 'created_at', 'last_searched_at')
    list_filter = ('created_at', 'last_searched_at')
    search_fields = ('query_text', 'user__username', 'user__email')
    readonly_fields = ('user', 'query_text', 'filters', 'created_at', 'last_searched_at')
    list_select_related = ('user',)
    raw_id_fields = ('user',)
    ordering = ('-last_searched_at',)

@admin.register(ViewHistory)
class ViewHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'item', 'created_at', 'last_viewed_at')
    list_filter = ('created_at', 'last_viewed_at')
    search_fields = ('user__username', 'user__email', 'item__name')
    readonly_fields = ('user', 'item', 'created_at', 'last_viewed_at')
    list_select_related = ('user', 'item')
    raw_id_fields = ('user', 'item')
    ordering = ('-last_viewed_at',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'author', 'recipient', 'transaction', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'author__username', 'recipient__username', 'item__name')
    readonly_fields = ('author', 'recipient', 'transaction', 'item', 'created_at', 'updated_at')
    list_select_related = ('author', 'recipient', 'item', 'transaction')
    raw_id_fields = ('author', 'recipient', 'transaction', 'item')


@admin.register(FavoriteItem)
class FavoriteItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'item', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'item__name')
    readonly_fields = ('user', 'item', 'created_at')
    list_select_related = ('user', 'item')
    raw_id_fields = ('user', 'item')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'kind', 'item', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read', 'created_at')
    search_fields = ('user__username', 'user__email', 'item__name', 'message')
    readonly_fields = ('user', 'kind', 'item', 'message', 'created_at')
    list_select_related = ('user', 'item')
    raw_id_fields = ('user', 'item')