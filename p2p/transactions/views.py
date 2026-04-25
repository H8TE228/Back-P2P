from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema

from .models import Transaction
from .serializers import TransactionSerializer
from .permissions import CanApproveTransaction, CanReturnItem


# создать транзакцию (запрос на аренду), 
# получить список транзакций пользователя на данный предмет 
class ItemTransactionView(APIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["transactions"],
        summary="Создать транзакцию для айтема (арендовать предмет)",
        description="""
            Создаёт транзакцию для предмета (пользователь нажал "арендовать").
            После создания транзакции, она получает статус 'PENDING',
            т.е. она ещё должна получить от владельца предмета одобрение на аренду.
            (см. transactions/pending/)

            Статусы у транзакции:
            PENDING -> APPROVED (или REJECTED) -> ACTIVE -> RETURNING -> COMPLETED
        """
    )
    def post(self, request, item_id):
        transaction, created = Transaction.objects.get_or_create(
            item_id = item_id,
            renter = request.user,
            defaults={'status': 'pending'},
        )
        if not created:
            return Response(
                {"detail": "Данный предмет в настойщий момент уже находится в со-владении у этого пользователя"},
                status=status.HTTP_400_BAD_REQUEST
            )
        transaction.save()
        return Response(status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["transactions"],
        summary="Список транзакций пользователя с данным предметом",
        description="""
            Возвращает список транзакций, в которых пользователь арендовывал данный предмет.
            Возвращает список, так как у пользователя могло быть несколько аренд данного предмета в прошлом.
        """
    )
    def get(self, request, item_id):
        transactions = Transaction.objects.filter(renter=request.user, item_id=item_id)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


# список транзакций юзера
@extend_schema(
    tags=["transactions"],
    summary="Список всех транзакций пользователя",
    description="""
        Возвращает список всех транзакций пользователя, в которых он участвовал либо как владелец предмета,
        либо как пользователь, арендующий предмет.
        Доступна фильтрация по item, owner и status.
    """
)
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

    @extend_schema(
        tags=["transactions"],
        summary="Получить транзакцию по id",
        description="""
            Возвращает транзакцию по её id.
        """
    )
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
@extend_schema(
    tags=["transactions"],
    summary="Список транзакций, ожидающих подтверждения",
    description="""
        Возвращает список транзакций, которые пользователь должен подтвердить.
        Вот какие транзакции возвращает данный эндпоинт:
            - Транзакции со статусом 'PENDING' - это заявки от пользователей, которые хотят арендовать предмет текущего юзера.
            Такие транзакции можно либо одобрить, и тогда статус сменится на 'APPROVED', либо можно отказать, и тогда
            статус сменится на 'REJECTED'. (см. /transactions/approve/ и /transactions/reject/)  
            - Транзакции со статусом 'APPROVED' - это одобренные транзакции текущего пользователя.
            Данный статус имеют транзакции на те вещи, аренду которых уже одобрил их владелец, но сам арендатор ещё их
            не получил. (Условно, рентер видит на сайте трактор и нажимает "арендовать", после чего создаётся транзакция
            со статусом 'PENDING', владелец трактора одобряет аренду и статус меняется на 'APPROVED', после чего уже рентер
            подтверждает, что он этот трактор получил, и статус вновь меняется уже на 'ACTIVE'.)
            - Транзакции со статусом 'RETURNING' - рентер захотел вернуть предмет, и до тех пор, пока владелец
            не подтвердит, что предмет ему вернули, транзакция имеет статус 'RETURNING' a.k.a. в процессе возвращения.

        Статусы у транзакции:
        PENDING -> APPROVED (или REJECTED) -> ACTIVE -> RETURNING -> COMPLETED
        Запрос на аренду -> запрос подтвердили (или отклонили) -> сделка активна -> в процессе возврата -> завершена
    """
)
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
    
    @extend_schema(
        tags=["transactions"],
        summary="Подтвердить смену статуса транзакции",
        description="""
            Данный эндпоинт используется для подтверждения транзакции пользователем:
             - Если пользователь это владелец и кто-то хочет арендовать его вещь, то владелец сначала должен либо
                одобрить данную транзакцию (аренду), либо отказать. Для одобрения и используется данный эндпоинт.
             - Если пользователь это арендатель и владелец одобрил аренду, то тут рентер подтверждает, что он получил
                тот предмет, который арендовал.
             - Если пользователь это владелец и ему должны вернуть предмет после аренды, то тут владелец подтверждает,
                что он получил свой предмет обратно.
        """
    )
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
    
    @extend_schema(
        tags=["transactions"],
        summary="Отказать арендателю в аренде предмета",
        description="""
            Владелец предмета может отказать в аренде на предмет.
            Меняет статус транзакции на 'REJECTED'
        """
    )
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

    @extend_schema(
        tags=["transactions"],
        summary="Вернуть предмет",
        description="""
            Меняет статус транзакции на 'RETURNING', когда рентер решает вренуть предмет, но сам
            владелец ещё не подтвердил, что получил предмет обратно.
        """
    )
    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        self.check_object_permissions(request, transaction)
        transaction.status = Transaction.Status.RETURNING
        transaction.save()

        return Response({
            "id": transaction.id,
            "new_status": transaction.status
        }, status=status.HTTP_200_OK)