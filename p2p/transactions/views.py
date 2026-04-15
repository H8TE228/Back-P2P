from django.shortcuts import get_object_or_404

from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Transaction
from .serializers import TransactionSerializer

class TransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        transaction, created = Transaction.objects.get_or_create(
            item_id = item_id,
            renter = request.user,
            is_active = True,
        )
        if not created:
            return Response({"detail": "Данный предмет в настойщий момент уже находится в со-владении у этого пользователя"}, status=status.HTTP_400_BAD_REQUEST)
        transaction.save()
        return Response(status=status.HTTP_201_CREATED)

    def get(self, request, item_id):
        transactions = Transaction.objects.filter(renter=request.user, item_id=item_id)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
class TransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id, pk):
        transaction = get_object_or_404(Transaction, item_id=item_id, id=pk)
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)
    
    def patch(self, request, item_id, pk):
        transaction = get_object_or_404(Transaction, item_id=item_id, id=pk)
        serializer = TransactionSerializer(transaction, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)