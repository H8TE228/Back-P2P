from django.utils import timezone
from rest_framework import serializers
from .models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    renter_name = serializers.ReadOnlyField(source='renter.username')
    owner_name = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Transaction
        fields = [
            'id', 'owner', 'renter', 'item', 'rented_at',
            'status', 'returned_at',
            'item_name', 'renter_name', 'owner_name',
            'planned_start', 'planned_end',
        ]
        read_only_fields = [
            'id', 'owner', 'renter', 'item', 'rented_at',
            'status', 'returned_at',
            'item_name', 'renter_name', 'owner_name',
        ]

    def validate_planned_start(self, value):
        if value < timezone.now():
            raise serializers.ValidationError('Дата не может быть в прошлом')
        return value

    def validate(self, data):
        if data['planned_start'] > data['planned_end']:
            raise serializers.ValidationError({
                "end_date": "Дата окончания не может быть раньше даты начала."
            })
        return data

