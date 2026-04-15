from rest_framework import serializers
from .models import Category, ItemType, Item, ItemImage, SearchHistory, ViewHistory, FavoriteCategory # Review,
from django.contrib.auth import get_user_model

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ItemTypeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = ItemType
        fields = [
            'id', 'category', 'category_name', 'name', 'usage_tips', 
            'safety_rules', 'inspection_checklist', 'characteristics_template',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ['id', 'url', 'alt_text', 'is_main']

class ItemSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source='type.name', read_only=True)
    category_name = serializers.CharField(source='type.category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    images = ItemImageSerializer(many=True, required=False)

    class Meta:
        model = Item
        fields = [
            'id', 'type', 'type_name', 'category_name', 'owner', 'owner_name',
            'name', 'description', 'characteristics', 'status', 'price',
            'images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        item = Item.objects.create(**validated_data)
        for image_data in images_data:
            ItemImage.objects.create(item=item, **image_data)
        return item

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if images_data is not None:
            instance.images.all().delete()
            for image_data in images_data:
                ItemImage.objects.create(item=instance, **image_data)
        
        return instance

# class ReviewSerializer(serializers.ModelSerializer):
#     author_name = serializers.CharField(source='author.username', read_only=True)
#     item_name = serializers.CharField(source='item.name', read_only=True)

#     class Meta:
#         model = Review
#         fields = [
#             'id', 'author', 'author_name', 'transaction', 'item', 'item_name',
#             'rating', 'comment', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'author', 'created_at', 'updated_at']

class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ['id', 'query_text', 'filters', 'created_at']
        read_only_fields = ['id', 'created_at']

class ViewHistorySerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = ViewHistory
        fields = ['id', 'item', 'item_name', 'created_at']
        read_only_fields = ['id', 'created_at']

class FavoriteCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )

    class Meta:
        model = FavoriteCategory
        fields = ['id', 'category', 'category_id', 'created_at']
        read_only_fields = ['id', 'created_at']