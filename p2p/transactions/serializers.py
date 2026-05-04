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
        ]
        read_only_fields = [
            'id', 'owner', 'renter', 'item', 'rented_at',
            'status', 'returned_at',
            'item_name', 'renter_name', 'owner_name',
        ]
