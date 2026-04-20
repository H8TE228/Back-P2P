from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Transaction
from .serializers import TransactionSerializer
from .permissions import CanApproveTransaction, CanReturnItem


# создать транзакцию (запрос на аренду), 
# получить список транзакций пользователя на данный предмет 
class ItemTransactionView(APIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        transaction, created = Transaction.objects.get_or_create(
            item_id = item_id,
            renter = request.user,
            defaults={'status': 'pending'},
        )
        if not created:
            return Response({"detail": "Данный предмет в настойщий момент уже находится в со-владении у этого пользователя"}, status=status.HTTP_400_BAD_REQUEST)
        transaction.save()
        return Response(status=status.HTTP_201_CREATED)

    def get(self, request, item_id):
        transactions = Transaction.objects.filter(renter=request.user, item_id=item_id)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


# список транзакций юзера
class UserTransactionView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'item', 'owner']

    def get_queryset(self):
        return Transaction.objects.filter(Q(owner=self.request.user) | Q(renter=self.request.user))


# получить транзакцию по pk
class TransactionDetailView(APIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        transaction = get_object_or_404(Transaction, id=pk)
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)
    
    # def patch(self, request, pk):
    #     transaction = get_object_or_404(Transaction, id=pk)
    #     serializer = TransactionSerializer(transaction, data=request.data, partial=True)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# список транзакций, на которые необходимо ответить подтверждением
class PendingTransactionsView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(
            Q(owner=self.request.user, status__in=[Transaction.Status.PENDING, Transaction.Status.RETURNING]) |
            Q(renter=self.request.user, status=Transaction.Status.APPROVED)
        )


# подтвердить транзакцию (одобрить, подтвердить получение/возврат предмета)
class TransactionApprovalView(APIView):
    permission_classes = [IsAuthenticated, CanApproveTransaction,]
    
    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        self.check_object_permissions(request, transaction)

        match transaction.status:
            case Transaction.Status.PENDING:
                transaction.status = Transaction.Status.APPROVED
            case Transaction.Status.APPROVED:
                transaction.status = Transaction.Status.ACTIVE
            case Transaction.Status.RETURNING:
                transaction.status = Transaction.Status.COMPLETED
                transaction.returned_at = timezone.now()

        transaction.save()
        return Response({
            "id": transaction.id,
            "new_status": transaction.status
        }, status=status.HTTP_200_OK)
    

# reject
class TransactionRejectionView(APIView):
    permission_classes = [IsAuthenticated, CanApproveTransaction]
    
    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        self.check_object_permissions(request, transaction)
        if transaction.status != Transaction.Status.PENDING:
            return Response(
                {"error": "Можно отклонить только навый запрос"},
                status=status.HTTP_400_BAD_REQUEST
            )
        transaction.status = Transaction.Status.REJECTED
        transaction.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
        


# послать запрос на возвращение предмета
class ReturnItemView(APIView):
    permission_classes = [IsAuthenticated, CanReturnItem]
    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        self.check_object_permissions(request, transaction)
        transaction.status = Transaction.Status.RETURNING
        transaction.save()

        return Response({
            "id": transaction.id,
            "new_status": transaction.status
        }, status=status.HTTP_200_OK)