from rest_framework import serializers
from .models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'owner', 'renter', 'item', 'rented_at',
            'status', 'returned_at',
        ]
        read_only_fields = [
            'id', 'owner', 'renter', 'item', 'rented_at',
            'status', 'returned_at',
        ]
