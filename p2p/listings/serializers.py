from rest_framework import serializers
from .models import Category, ItemType, Item, ItemImage, Notification, SearchHistory, ViewHistory, FavoriteCategory, FavoriteItem, Review
from django.contrib.auth import get_user_model

from users.serializers import UserSerializer


User = get_user_model()

class CategoryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemType
        fields = ['id', 'name']

class CategorySerializer(serializers.ModelSerializer):
    types = CategoryTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'types', 'created_at', 'updated_at']
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
        fields = ['id', 'item', 'image', 'alt_text', 'is_main', 'created_at']
        read_only_fields = ['id', 'created_at']

class AvailabilityCalendarSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()

    def validate(self, data):
        if data['start'] >= data['end']:
            raise serializers.ValidationError("Конец не может быть перед началом")
        return data

class ItemSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source='type.name', read_only=True)
    category_name = serializers.CharField(source='type.category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    images = ItemImageSerializer(many=True, read_only=True)
    availability_calendar = AvailabilityCalendarSerializer(many=True, required=False)

    class Meta:
        model = Item
        fields = [
            'id', 'type', 'type_name', 'category_name', 'owner', 'owner_name',
            'name', 'description', 'characteristics', 'status', 'price',
            'images', 'created_at', 'updated_at',
            'delivery_method', 'max_active_transactions',
            'availability_calendar',
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
    
    def validate_availability_calendar(self, value):
        sorted_dates = sorted(value, key=lambda x: x['start'])
        for i in range(len(sorted_dates) - 1):
            current_slot = sorted_dates[i]
            next_slot = sorted_dates[i+1]
            if next_slot['start'] < current_slot['end']:
                raise serializers.ValidationError(
                    f'Интервалы пересекаются: end {current_slot["end"]} накладывается на {next_slot["start"]}'
                )
        return value


class ItemDetailOwnerSerializer(UserSerializer):
    
    class Meta(UserSerializer.Meta):
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'phone_number', 'profile_picture',
            'country', 'region', 'city', 'district',
            'rating', 'reviews_count',
        )
        read_only_fields = ('id', 'rating', 'reviews_count')


class ItemDetailSerializer(ItemSerializer):
    owner = ItemDetailOwnerSerializer(read_only=True)

    class Meta(ItemSerializer.Meta):
        fields = ItemSerializer.Meta.fields


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    recipient_name = serializers.CharField(source='recipient.username', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'author', 'author_name', 'recipient', 'recipient_name',
            'transaction', 'item', 'item_name',
            'rating', 'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'item', 'recipient', 'created_at', 'updated_at']

    def validate_transaction(self, value):
        if value.status != 'completed':
            raise serializers.ValidationError(
                "Отзыв можно оставить только после завершения транзакции"
            )
        author = self.context['request'].user
        if author not in [value.owner, value.renter]:
            raise serializers.ValidationError(
                "Только участники транзакции могут оставить отзыв"
            )
        if Review.objects.filter(transaction=value, author=author).exists():
            raise serializers.ValidationError(
                "Вы уже оставили отзыв на эту транзакцию"
            )
        return value

    def create(self, validated_data):
        transaction = validated_data['transaction']
        author = self.context['request'].user

        if author == transaction.renter:
            validated_data['recipient'] = transaction.owner
        else:
            validated_data['recipient'] = transaction.renter

        validated_data['author'] = author
        validated_data['item'] = transaction.item
        return super().create(validated_data)

class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ['id', 'query_text', 'filters', 'created_at', 'last_searched_at']
        read_only_fields = ['id', 'created_at', 'last_searched_at']

class ViewHistorySerializer(serializers.ModelSerializer):
    item = ItemDetailSerializer(read_only=True)
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source='item', write_only=True, required=False
    )

    class Meta:
        model = ViewHistory
        fields = ['id', 'item', 'item_id', 'created_at', 'last_viewed_at']
        read_only_fields = ['id', 'created_at', 'last_viewed_at']

class FavoriteCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )

    class Meta:
        model = FavoriteCategory
        fields = ['id', 'category', 'category_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class FavoriteItemSerializer(serializers.ModelSerializer):
    item = ItemDetailSerializer(read_only=True)
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source='item', write_only=True
    )

    class Meta:
        model = FavoriteItem
        fields = ['id', 'item', 'item_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'kind', 'item', 'item_name', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'kind', 'item', 'item_name', 'message', 'created_at']