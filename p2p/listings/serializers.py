from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import (
    Category, ItemType, Item, ItemImage, Notification,
    SearchHistory, ViewHistory, FavoriteCategory, FavoriteItem, Review,
    SharedRental, SharedRentalSegment,
)
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
    related_types = CategoryTypeSerializer(many=True, read_only=True)

    class Meta:
        model = ItemType
        fields = [
            'id', 'category', 'category_name', 'name', 'usage_tips',
            'safety_rules', 'inspection_checklist', 'characteristics_template',
            'related_types',
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
    effective_status = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            'id', 'type', 'type_name', 'category_name', 'owner', 'owner_name',
            'name', 'description', 'characteristics', 'status', 'effective_status', 'is_liked', 'price',
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

    @extend_schema_field(serializers.CharField())
    def get_effective_status(self, obj):
        """
        Вычисляемый статус: 'rented', если у предмета сейчас есть активная
        одиночная или групповая аренда (active/returning). Иначе — то, что в БД.
        Фронт должен использовать это поле для отображения, а не `status`.
        """
        active_states = ('active', 'returning')
        if obj.transactions.filter(status__in=active_states).exists():
            return 'rented'
        if obj.shared_rentals.filter(status__in=active_states).exists():
            return 'rented'
        return obj.status
    
    @extend_schema_field(serializers.BooleanField())
    def get_is_liked(self, obj):
        """
        Лайкнут ли товар текущим пользователем (есть ли FavoriteItem).
        Для анонимных всегда False.

        Кэшируем множество liked-item-id в context, чтобы при сериализации
        списка (many=True) не делать N+1 запросов. Один запрос вместо N.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        if '_liked_ids' not in self.context:
            self.context['_liked_ids'] = set(
                FavoriteItem.objects.filter(user=request.user)
                .values_list('item_id', flat=True)
            )
        return obj.id in self.context['_liked_ids']
    
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


class SharedRentalSegmentSerializer(serializers.ModelSerializer):
    participant_name = serializers.CharField(source='participant.username', read_only=True)
    is_free = serializers.SerializerMethodField()
    days_count = serializers.SerializerMethodField()

    class Meta:
        model = SharedRentalSegment
        fields = [
            'id', 'segment_index', 'segment_start', 'segment_end',
            'participant', 'participant_name', 'is_free', 'days_count', 'joined_at',
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField())
    def get_is_free(self, obj):
        return obj.participant_id is None

    @extend_schema_field(serializers.IntegerField())
    def get_days_count(self, obj):
        return (obj.segment_end - obj.segment_start).days


class SharedRentalSerializer(serializers.ModelSerializer):
    item_detail = ItemDetailSerializer(source='item', read_only=True)
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    segments = SharedRentalSegmentSerializer(many=True, read_only=True)
    participants_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    days_per_slot = serializers.SerializerMethodField()
    creator_segment_index = serializers.IntegerField(write_only=True, required=True, min_value=0)
    viewer_role = serializers.SerializerMethodField()

    class Meta:
        model = SharedRental
        fields = [
            'id', 'item', 'item_detail',
            'creator', 'creator_name',
            'planned_start', 'planned_end', 'slots_needed',
            'creator_segment_index',
            'status', 'segments',
            'participants_count', 'is_full', 'days_per_slot',
            'viewer_role',
            'confirmed_received_at', 'confirmed_returned_at', 'completed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'creator', 'status', 'segments',
            'participants_count', 'is_full', 'days_per_slot',
            'viewer_role',
            'confirmed_received_at', 'confirmed_returned_at', 'completed_at',
            'created_at', 'updated_at',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_days_per_slot(self, obj):
        total_days = (obj.planned_end - obj.planned_start).days
        return total_days // obj.slots_needed if obj.slots_needed else 0

    def validate(self, data):
        from django.utils import timezone

        if data['planned_start'] < timezone.now():
            raise serializers.ValidationError({"planned_start": "Дата не может быть в прошлом"})
        if data['planned_start'] >= data['planned_end']:
            raise serializers.ValidationError("planned_end должен быть после planned_start")

        total_days = (data['planned_end'] - data['planned_start']).days
        if total_days <= 0:
            raise serializers.ValidationError("Период должен быть минимум один день")

        slots = data['slots_needed']
        if slots < 2:
            raise serializers.ValidationError({"slots_needed": "Минимум 2 участника"})

        if total_days % slots != 0:
            raise serializers.ValidationError(
                f"Период ({total_days} дней) не делится поровну на {slots} участников. "
                f"Возможные варианты для этого периода: делители {total_days}."
            )

        idx = data.get('creator_segment_index')
        if idx is None or idx < 0 or idx >= slots:
            raise serializers.ValidationError({
                "creator_segment_index": f"Индекс сегмента должен быть от 0 до {slots - 1}"
            })

        item = data['item']
        request = self.context.get('request')
        if request and item.owner == request.user:
            raise serializers.ValidationError("Нельзя арендовать собственный предмет")

        # проверка пересечений с availability_calendar предмета
        new_start = data['planned_start'].isoformat()
        new_end = data['planned_end'].isoformat()
        for entry in (item.availability_calendar or []):
            if new_start < entry['end'] and new_end > entry['start']:
                raise serializers.ValidationError(
                    f"Период пересекается с уже забронированным интервалом "
                    f"({entry['start']} — {entry['end']})"
                )

        return data

    def create(self, validated_data):
        from django.utils import timezone
        from datetime import timedelta

        creator_segment_index = validated_data.pop('creator_segment_index')
        creator = self.context['request'].user
        validated_data['creator'] = creator

        shared_rental = SharedRental.objects.create(**validated_data)

        total_days = (shared_rental.planned_end - shared_rental.planned_start).days
        days_per_slot = total_days // shared_rental.slots_needed

        for i in range(shared_rental.slots_needed):
            seg_start = shared_rental.planned_start + timedelta(days=i * days_per_slot)
            seg_end = shared_rental.planned_start + timedelta(days=(i + 1) * days_per_slot)
            SharedRentalSegment.objects.create(
                shared_rental=shared_rental,
                segment_index=i,
                segment_start=seg_start,
                segment_end=seg_end,
                participant=creator if i == creator_segment_index else None,
                joined_at=timezone.now() if i == creator_segment_index else None,
            )

        return shared_rental
    @extend_schema_field(serializers.CharField())
    def get_viewer_role(self, obj):
        """
        Роль текущего пользователя относительно этой заявки:
        - 'owner'       — владелец предмета
        - 'creator'     — создатель заявки
        - 'participant' — участник (не создатель)
        - 'guest'       — посторонний (или анонимный)
        Помогает фронту понять, какие кнопки показывать.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 'guest'
        user = request.user
        if obj.item.owner_id == user.id:
            return 'owner'
        if obj.creator_id == user.id:
            return 'creator'
        if obj.segments.filter(participant=user).exists():
            return 'participant'
        return 'guest'