from django.contrib import admin
from .models import Category, Listing, ListingImage

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent']
    list_filter = ['parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'owner',
        'category',
        'price',
        'status',
        'created_at',
        'updated_at'
    ]
    list_filter = ['status', 'category', 'created_at', 'updated_at']
    search_fields = ['title', 'description', 'owner__email', 'owner__username']
    readonly_fields = ['owner', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'owner', 'category', 'status')
        }),
        ('Цена', {
            'fields': ('price',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        # Если это создание нового объекта и владелец не указан
        if not change and not obj.owner:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ['listing', 'image', 'is_primary', 'uploaded_at']
    list_filter = ['is_primary', 'uploaded_at']
    readonly_fields = ['uploaded_at']