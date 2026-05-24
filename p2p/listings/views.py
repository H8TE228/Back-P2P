from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ItemFilter
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from drf_spectacular.utils import extend_schema


from .models import (
    Category, ItemType, Item, ItemImage, Notification,
    SearchHistory, ViewHistory, FavoriteCategory, FavoriteItem,
    Review,
    SharedRental, SharedRentalSegment,
)
from .serializers import (
    CategorySerializer, ItemTypeSerializer, ItemSerializer, ItemImageSerializer, NotificationSerializer,
    SearchHistorySerializer, ViewHistorySerializer, FavoriteCategorySerializer,
    FavoriteItemSerializer,
    ReviewSerializer, ItemDetailSerializer,
    SharedRentalSerializer,
)

@extend_schema(
    tags=["item categories"],
    description="""
        CRUD для категорий айтемов
        Категория предмета -> тип предмета -> предмет
        Пример: транспорт -> трактор -> item 'трактор модель XXXX (красный)' от user_id=1
    """
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


@extend_schema(
    tags=["item types"],
    description="""
        CRUD для типов айтемов
        Категория предмета -> тип предмета -> предмет
        Пример: транспорт -> трактор -> item 'трактор модель XXXX (красный)' от user_id=1
    """
)
class ItemTypeViewSet(viewsets.ModelViewSet):
    queryset = ItemType.objects.all()
    serializer_class = ItemTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        queryset = ItemType.objects.all()
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset


@extend_schema(
    tags=["items"],
    description="""
        CRUD для предмета
    """
)
class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ItemFilter

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return ItemDetailSerializer
        return ItemSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        queryset = Item.objects.all()
        
        type_id = self.request.query_params.get('type', None)
        if type_id:
            queryset = queryset.filter(type_id=type_id)

        owner_id = self.request.query_params.get('owner', None)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
            
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
            
        if self.action in ['retrieve', 'list']:
            return queryset.select_related('owner')
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        try:
            from .services import log_item_search
            log_item_search(request.user, request.query_params)
        except Exception:
            # не валим запрос из-за проблем с историей поиска
            pass
        return response
    

    @extend_schema(
        tags=["recommendations"],
        summary="Сопутствующие товары",
        description="""
            Возвращает товары типов, связанных с типом текущего предмета через
            ItemType.related_types. Например, к палатке вернёт спальники и горелки,
            если в админке настроены такие связи.

            Возвращает до 20 элементов, только со статусом available.
        """,
    )
    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        item = self.get_object()
        related_type_ids = list(item.type.related_types.values_list('id', flat=True))
        if not related_type_ids:
            return Response([])

        qs = Item.objects.filter(
            type_id__in=related_type_ids,
            status='available',
        ).exclude(pk=item.pk).select_related(
            'owner', 'type', 'type__category',
        ).prefetch_related('images').order_by('-created_at')[:20]

        serializer = ItemDetailSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        tags=["recommendations"],
        summary="Похожие товары",
        description="""
            Возвращает товары того же типа, что и текущий, исключая сам товар
            и (если запрашивает залогиненный пользователь) товары этого же пользователя.
            Возвращает до 20 элементов, только со статусом available.
        """,
    )
    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        item = self.get_object()
        qs = Item.objects.filter(
            type_id=item.type_id,
            status='available',
        ).exclude(pk=item.pk)

        if request.user.is_authenticated:
            qs = qs.exclude(owner=request.user)

        qs = qs.select_related(
            'owner', 'type', 'type__category',
        ).prefetch_related('images').order_by('-created_at')[:20]

        serializer = ItemDetailSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class ItemImageViewSet(viewsets.ModelViewSet):
    queryset = ItemImage.objects.all()
    serializer_class = ItemImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = ItemImage.objects.all()
        item_id = self.request.query_params.get('item')
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        return queryset

    def perform_create(self, serializer):
        item = serializer.validated_data['item']
        if item.owner != self.request.user:
            raise PermissionDenied("Вы не владелец этого предмета")
        serializer.save()

    def perform_update(self, serializer):
        if serializer.instance.item.owner != self.request.user:
            raise PermissionDenied("Вы не владелец этого предмета")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.item.owner != self.request.user:
            raise PermissionDenied("Вы не владелец этого предмета")
        instance.delete()


@extend_schema(
    tags=["items"],
    summary="Список айтемов юзера",
    description="""
        Возвращает список принадлежащих юзеру айтемов
    """
)
class MyItemsView(generics.ListAPIView):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status',]
    queryset = Item.objects.none()

    def get_queryset(self):
        return Item.objects.filter(owner=self.request.user)


@extend_schema(
    tags=["reviews"],
    description="""
        CRUD для отзывов
    """
)
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Review.objects.select_related(
            'author', 'recipient', 'item', 'transaction'
        ).all()

        item_id = self.request.query_params.get('item_id')
        recipient_id = self.request.query_params.get('recipient_id')
        author_id = self.request.query_params.get('author_id')
        transaction_id = self.request.query_params.get('transaction_id')

        if item_id:
            queryset = queryset.filter(item_id=item_id)
        if recipient_id:
            queryset = queryset.filter(recipient_id=recipient_id)
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        if transaction_id:
            queryset = queryset.filter(transaction_id=transaction_id)
        return queryset

    @extend_schema(
        tags=["reviews"],
        summary="Отзывы, оставленные текущим пользователем",
        description="Возвращает все отзывы, где автор — текущий пользователь.",
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_reviews(self, request):
        reviews = self.get_queryset().filter(author=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["reviews"],
        summary="Отзывы, полученные текущим пользователем",
        description="Возвращает все отзывы, где получатель — текущий пользователь. Используется для вкладки «Отзывы» в профиле.",
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def received_reviews(self, request):
        reviews = self.get_queryset().filter(recipient=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["search history"],
    description="""
        CRUD для истории поиска пользователя по сайту
    """
)
class SearchHistoryViewSet(viewsets.ModelViewSet):
    queryset = SearchHistory.objects.all()
    serializer_class = SearchHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            user_id = self.kwargs.get('user_id')
            if user_id:
                return SearchHistory.objects.filter(user_id=user_id)
            return SearchHistory.objects.all()
        return SearchHistory.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


    @extend_schema(
        tags=["search history"],
        description="""
            Логирование поискового запроса (явное, по кнопке "Искать" с фронта).
            Принимает те же query-параметры, что и GET /listings/item/.
            Дедуплицируется так же, как автоматическое логирование:
            повторный одинаковый поиск не плодит дубли, обновляется last_searched_at.
        """
    )
    @action(detail=False, methods=['post'])
    def log_search(self, request):
        from .services import log_item_search
        params = request.query_params if request.query_params else request.data
        entry, created = log_item_search(request.user, params)
        if entry is None:
            return Response(
                {'detail': 'Пустой запрос — нечего логировать.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(entry)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@extend_schema(
    tags=["view history"],
    description="""
        История просмотров пользователя.
        Каждая пара (user, item) хранится одной записью.
        Повторный просмотр того же предмета не создаёт новую запись —
        обновляется только last_viewed_at.
    """
)
class ViewHistoryViewSet(viewsets.ModelViewSet):
    queryset = ViewHistory.objects.all()
    serializer_class = ViewHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = ViewHistory.objects.select_related(
            'item', 'item__owner', 'item__type', 'item__type__category',
        ).prefetch_related('item__images')

        if user.is_superuser:
            user_id = self.request.query_params.get('user_id')
            if user_id:
                return base_qs.filter(user_id=user_id)
            return base_qs.select_related('user')
        return base_qs.filter(user=user)

    def create(self, request, *args, **kwargs):
        item_id = request.data.get('item_id') or request.data.get('item')
        if not item_id:
            return Response(
                {'item': 'Это поле обязательно.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        view, created = ViewHistory.objects.update_or_create(
            user=request.user,
            item_id=item_id,
        )
        serializer = self.get_serializer(view)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["view history"],
        description="""
            Алиас для POST на /view-history/ — логирует просмотр предмета.
            Если просмотр уже был — обновляет last_viewed_at.
        """
    )
    @action(detail=False, methods=['post'])
    def log_view(self, request):
        return self.create(request)


@extend_schema(
    tags=["favorite item categories"],
    description="""
        CRUD для избранных категорий пользователя
    """
)
class FavoriteCategoryViewSet(viewsets.ModelViewSet):
    queryset = FavoriteCategory.objects.all()
    serializer_class = FavoriteCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return FavoriteCategory.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(
    tags=["favorite items"],
    description="""
        CRUD для избранных предметов пользователя.
        При добавлении предмета в избранное — запись будет создана,
        если её ещё нет (повтор не плодит дубли).
        Когда предмет освобождается из аренды (active/returning -> completed),
        пользователю автоматически создаётся уведомление (см. /notifications/).
    """
)
class FavoriteItemViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteItem.objects.filter(
            user=self.request.user
        ).select_related(
            'item', 'item__type', 'item__type__category', 'item__owner'
        ).prefetch_related('item__images')

    def create(self, request, *args, **kwargs):
        item_id = request.data.get('item_id') or request.data.get('item')
        if not item_id:
            return Response(
                {'item_id': 'Это поле обязательно.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        item = get_object_or_404(Item, pk=item_id)
        favorite, created = FavoriteItem.objects.get_or_create(
            user=request.user,
            item=item,
        )
        serializer = self.get_serializer(favorite)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
    
    @extend_schema(
        tags=["favorite items"],
        summary="Добавить/удалить избранное по id товара",
        description="""
            Управление избранным по `item_id`, а не по `favorite.id` — удобно,
            когда фронт знает только id товара (например, на странице товара).

            POST   /favorite-items/by-item/<item_id>/  — добавить (идемпотентно)
            DELETE /favorite-items/by-item/<item_id>/  — удалить из избранного

            Симметрично с полем Item.is_liked: фронт по одной кнопке делает toggle.
        """,
    )
    @action(
        detail=False,
        methods=['post', 'delete'],
        url_path='by-item/(?P<item_id>[0-9]+)',
    )
    def by_item(self, request, item_id=None):
        if request.method == 'POST':
            item = get_object_or_404(Item, pk=item_id)
            favorite, created = FavoriteItem.objects.get_or_create(
                user=request.user,
                item=item,
            )
            serializer = self.get_serializer(favorite)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        # DELETE
        deleted, _ = FavoriteItem.objects.filter(
            user=request.user, item_id=item_id,
        ).delete()
        if deleted == 0:
            return Response(
                {"detail": "Этого предмета нет в вашем избранном"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
    

@extend_schema(
    tags=["notifications"],
    description="""
        Уведомления текущего пользователя.
        GET /notifications/ — список (с пагинацией).
        PATCH /notifications/<id>/ — пометить как прочитанное (передать is_read=true).
        DELETE /notifications/<id>/ — удалить.
    """
)
class NotificationViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
    generics.mixins.UpdateModelMixin,
    generics.mixins.DestroyModelMixin,
):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).select_related('item')

    @extend_schema(
        tags=["notifications"],
        summary="Пометить все уведомления как прочитанные",
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'updated': updated})
    

@extend_schema(
    tags=["shared rentals"],
    description="""
        Групповая аренда (совладение).

        Несколько арендаторов берут один предмет на общий период и делят его
        на равные сегменты. Период должен делиться на количество участников нацело.

        Жизненный цикл:
        collecting → approved → active → returning → completed
        (или → cancelled / → expired)

        Эндпоинты:
        POST   /shared-rentals/                     — создать заявку
        GET    /shared-rentals/                     — список (фильтры: ?item=, ?status=, ?only_open=1, ?my=1)
        GET    /shared-rentals/<id>/                — детали с сегментами
        DELETE /shared-rentals/<id>/                — отменить (только создатель, только collecting)
        POST   /shared-rentals/<id>/join/           — присоединиться (нужно передать segment_index)
        POST   /shared-rentals/<id>/leave/          — выйти (только collecting, не для создателя)
        POST   /shared-rentals/<id>/approve/        — одобрить (только владелец, только когда is_full)
        POST   /shared-rentals/<id>/reject/         — отклонить (только владелец)
        POST   /shared-rentals/<id>/confirm-receipt/— подтвердить получение (любой участник, approved → active)
        POST   /shared-rentals/<id>/confirm-return/ — подтвердить возврат (любой участник, active → returning)
        POST   /shared-rentals/<id>/finalize/       — закрыть (только владелец, returning → completed)
        GET    /shared-rentals/my/                  — мои заявки (где я создатель или участник)
    """
)
class SharedRentalViewSet(viewsets.ModelViewSet):
    queryset = SharedRental.objects.all()
    serializer_class = SharedRentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']  # запрещаем PUT/PATCH

    def get_queryset(self):
        qs = SharedRental.objects.select_related(
            'item', 'item__owner', 'item__type', 'item__type__category', 'creator'
        ).prefetch_related(
            'item__images', 'segments', 'segments__participant',
        )

        item_id = self.request.query_params.get('item')
        status_param = self.request.query_params.get('status')
        only_open = self.request.query_params.get('only_open')
        my_flag = self.request.query_params.get('my')

        if item_id:
            qs = qs.filter(item_id=item_id)
        if status_param:
            qs = qs.filter(status=status_param)
        if only_open in ('1', 'true', 'True'):
            qs = qs.filter(status=SharedRental.Status.COLLECTING)
        if my_flag in ('1', 'true', 'True'):
            qs = qs.filter(
                Q(creator=self.request.user) |
                Q(segments__participant=self.request.user)
            ).distinct()

        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.maybe_expire()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.creator != request.user:
            raise PermissionDenied("Только создатель может отменить заявку")
        if instance.status != SharedRental.Status.COLLECTING:
            return Response(
                {"detail": f"Отменить можно только заявку в статусе 'collecting' (сейчас '{instance.status}')"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.status = SharedRental.Status.CANCELLED
        instance.save(update_fields=['status', 'updated_at'])
        self._notify_participants(
            instance,
            Notification.Kind.SHARED_RENTAL_CANCELLED,
            f'Групповая аренда «{instance.item.name}» отменена создателем',
            exclude_user=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["shared rentals"],
        summary="Заявки, требующие моего действия",
        description="""
            Возвращает групповые аренды, в которых я должен что-то сделать:
            - я владелец предмета, статус 'collecting' и набралось участников → нужен approve
            - я владелец предмета, статус 'returning' → нужен finalize
            - я участник, статус 'approved' → нужен confirm-receipt
            - я участник, статус 'active' → нужен confirm-return
        """,
    )
    @action(detail=False, methods=['get'])
    def pending(self, request):
        user = request.user
        all_segments = SharedRentalSegment.objects.filter(participant=user)
        my_sr_ids = all_segments.values_list('shared_rental_id', flat=True)

        qs = self.get_queryset()
        # как владелец предмета: collecting+is_full ИЛИ returning
        # как участник: approved ИЛИ active
        owner_collecting_full_or_returning = (
            Q(item__owner=user) &
            (
                Q(status=SharedRental.Status.RETURNING) |
                # отдельно соберём collecting и потом отфильтруем по is_full в Python:
                # фильтровать is_full на уровне БД через annotate — оверкилл для MVP
                Q(status=SharedRental.Status.COLLECTING)
            )
        )
        participant_approved_or_active = (
            Q(id__in=my_sr_ids) &
            Q(status__in=[SharedRental.Status.APPROVED, SharedRental.Status.ACTIVE])
        )

        qs = qs.filter(owner_collecting_full_or_returning | participant_approved_or_active)

        # отфильтруем collecting-но-не-full в Python (упрощённо для MVP)
        items = [
            sr for sr in qs
            if not (sr.status == SharedRental.Status.COLLECTING and not sr.is_full and sr.item.owner_id == user.id)
        ]

        page = self.paginate_queryset(items)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my(self, request):
        qs = self.get_queryset().filter(
            Q(creator=request.user) |
            Q(segments__participant=request.user)
        ).distinct()
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        shared = self.get_object()
        shared.maybe_expire()

        if shared.status != SharedRental.Status.COLLECTING:
            return Response(
                {"detail": f"Нельзя присоединиться к заявке со статусом '{shared.status}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if shared.item.owner == request.user:
            return Response(
                {"detail": "Владелец не может участвовать в аренде собственного предмета"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if shared.segments.filter(participant=request.user).exists():
            return Response(
                {"detail": "Вы уже участвуете в этой групповой аренде"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        segment_index = request.data.get('segment_index')
        if segment_index is None:
            return Response(
                {"segment_index": "Это поле обязательно. Укажите индекс свободного сегмента."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            segment_index = int(segment_index)
        except (TypeError, ValueError):
            return Response({"segment_index": "Должно быть целым числом"}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            try:
                segment = shared.segments.select_for_update().get(segment_index=segment_index)
            except SharedRentalSegment.DoesNotExist:
                return Response({"detail": "Сегмент с таким индексом не найден"}, status=status.HTTP_404_NOT_FOUND)

            if segment.participant_id is not None:
                return Response(
                    {"detail": "Этот сегмент уже занят"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from django.utils import timezone
            segment.participant = request.user
            segment.joined_at = timezone.now()
            segment.save()

        Notification.objects.create(
            user=shared.creator,
            kind=Notification.Kind.SHARED_RENTAL_JOINED,
            item=shared.item,
            message=f'{request.user.username} присоединился к вашей групповой аренде «{shared.item.name}»',
        )

        return Response(self.get_serializer(shared).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        shared = self.get_object()
        if shared.status != SharedRental.Status.COLLECTING:
            return Response(
                {"detail": f"Нельзя выйти из заявки со статусом '{shared.status}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if shared.creator == request.user:
            return Response(
                {"detail": "Создатель не может выйти из заявки. Чтобы прекратить, отмените её (DELETE)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        segment = shared.segments.filter(participant=request.user).first()
        if not segment:
            return Response(
                {"detail": "Вы не участвуете в этой групповой аренде"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        segment.participant = None
        segment.joined_at = None
        segment.save()
        return Response(self.get_serializer(shared).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        shared = self.get_object()
        if shared.item.owner != request.user:
            raise PermissionDenied("Только владелец предмета может одобрить групповую аренду")
        if shared.status != SharedRental.Status.COLLECTING:
            return Response(
                {"detail": f"Одобрить можно только заявку в статусе 'collecting' (сейчас '{shared.status}')"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not shared.is_full:
            return Response(
                {"detail": f"Все сегменты должны быть заняты ({shared.participants_count}/{shared.slots_needed})"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with db_transaction.atomic():
                shared.item.add_to_calendar(
                    user_id=shared.creator.pk,
                    start=shared.planned_start,
                    end=shared.planned_end,
                )
                shared.status = SharedRental.Status.APPROVED
                shared.save(update_fields=['status', 'updated_at'])
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        self._notify_participants(
            shared,
            Notification.Kind.SHARED_RENTAL_APPROVED,
            f'Владелец одобрил групповую аренду «{shared.item.name}»',
        )
        return Response(self.get_serializer(shared).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        shared = self.get_object()
        if shared.item.owner != request.user:
            raise PermissionDenied("Только владелец предмета может отклонить групповую аренду")
        if shared.status != SharedRental.Status.COLLECTING:
            return Response(
                {"detail": "Отклонить можно только заявку в статусе 'collecting'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shared.status = SharedRental.Status.CANCELLED
        shared.save(update_fields=['status', 'updated_at'])
        self._notify_participants(
            shared,
            Notification.Kind.SHARED_RENTAL_REJECTED,
            f'Владелец отклонил групповую аренду «{shared.item.name}»',
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='confirm-receipt')
    def confirm_receipt(self, request, pk=None):
        shared = self.get_object()
        if not shared.segments.filter(participant=request.user).exists():
            raise PermissionDenied("Только участник группы может подтвердить получение")
        if shared.status != SharedRental.Status.APPROVED:
            return Response(
                {"detail": f"Получение можно подтвердить только в статусе 'approved' (сейчас '{shared.status}')"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        shared.status = SharedRental.Status.ACTIVE
        shared.confirmed_received_at = timezone.now()
        shared.save(update_fields=['status', 'confirmed_received_at', 'updated_at'])
        return Response(self.get_serializer(shared).data)

    @action(detail=True, methods=['post'], url_path='confirm-return')
    def confirm_return(self, request, pk=None):
        shared = self.get_object()
        if not shared.segments.filter(participant=request.user).exists():
            raise PermissionDenied("Только участник группы может подтвердить возврат")
        if shared.status != SharedRental.Status.ACTIVE:
            return Response(
                {"detail": f"Возврат можно подтвердить только в статусе 'active' (сейчас '{shared.status}')"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        shared.status = SharedRental.Status.RETURNING
        shared.confirmed_returned_at = timezone.now()
        shared.save(update_fields=['status', 'confirmed_returned_at', 'updated_at'])
        return Response(self.get_serializer(shared).data)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        shared = self.get_object()
        if shared.item.owner != request.user:
            raise PermissionDenied("Только владелец предмета может завершить аренду")
        if shared.status != SharedRental.Status.RETURNING:
            return Response(
                {"detail": f"Завершить можно только в статусе 'returning' (сейчас '{shared.status}')"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        shared.status = SharedRental.Status.COMPLETED
        shared.completed_at = timezone.now()
        shared.save(update_fields=['status', 'completed_at', 'updated_at'])
        self._notify_favoriters(shared.item)
        return Response(self.get_serializer(shared).data)

    # хелперы
    @staticmethod
    def _notify_participants(shared, kind, message, exclude_user=None):
        qs = SharedRentalSegment.objects.filter(
            shared_rental=shared,
            participant__isnull=False,
        )
        if exclude_user:
            qs = qs.exclude(participant=exclude_user)
        user_ids = qs.values_list('participant_id', flat=True).distinct()
        notifications = [
            Notification(user_id=uid, kind=kind, item=shared.item, message=message)
            for uid in user_ids
        ]
        if notifications:
            Notification.objects.bulk_create(notifications)

    @staticmethod
    def _notify_favoriters(item):
        favoriters = FavoriteItem.objects.filter(item=item).select_related('user')
        notifications = [
            Notification(
                user=fav.user,
                kind=Notification.Kind.FAVORITE_ITEM_AVAILABLE,
                item=item,
                message=f'Предмет «{item.name}» снова доступен для аренды',
            )
            for fav in favoriters
        ]
        if notifications:
            Notification.objects.bulk_create(notifications)


@extend_schema(
    tags=["shared rentals"],
    summary="Создать групповую аренду для конкретного предмета",
    description="""
        Удобная ручка для создания заявки на групповую аренду через URL предмета —
        симметрично с обычной арендой POST /listings/<item_id>/transactions/.
        В body НЕ нужно передавать `item` — он берётся из URL.

        Поля в body:
        - planned_start (ISO datetime)
        - planned_end   (ISO datetime)
        - slots_needed  (int >= 2)
        - creator_segment_index (int, 0..slots_needed-1)
    """,
)
class ItemSharedRentalView(generics.CreateAPIView):
    serializer_class = SharedRentalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        item_id = self.kwargs['item_id']
        # подмешиваем item в данные перед валидацией
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['item'] = item_id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

@extend_schema(
    tags=["recommendations"],
    summary="Персональные рекомендации",
    description="""
        Возвращает рекомендации для текущего пользователя на основе истории просмотров.

        Алгоритм:
        1. Берём топ-5 типов предметов из ViewHistory пользователя.
        2. К ним добавляем все related_types (сопутствующие).
        3. Из items этих типов оставляем только available.
        4. Исключаем свои предметы и уже просмотренные.
        5. Сортировка: новые сверху, лимит 20.

        Если истории просмотров нет — возвращает 20 свежих available items
        (исключая свои), как fallback.

        Формат ответа — массив, не пагинированный объект (для совместимости с
        /item/<id>/recommendations/ и /item/<id>/similar/).
    """,
)
class PersonalRecommendationsView(generics.GenericAPIView):
    serializer_class = ItemDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        viewed_type_ids = list(
            ViewHistory.objects.filter(user=user)
            .values_list('item__type_id', flat=True)
            .distinct()[:5]
        )

        base_qs = Item.objects.filter(status='available').exclude(owner=user)

        if not viewed_type_ids:
            qs = base_qs.select_related(
                'owner', 'type', 'type__category',
            ).prefetch_related('images').order_by('-created_at')[:20]
        else:
            all_type_ids = set(viewed_type_ids)
            related = ItemType.objects.filter(
                id__in=viewed_type_ids,
            ).values_list('related_types__id', flat=True)
            all_type_ids.update(t_id for t_id in related if t_id is not None)

            viewed_item_ids = ViewHistory.objects.filter(user=user).values_list('item_id', flat=True)

            qs = base_qs.filter(
                type_id__in=all_type_ids,
            ).exclude(
                id__in=viewed_item_ids,
            ).select_related(
                'owner', 'type', 'type__category',
            ).prefetch_related('images').order_by('-created_at')[:20]

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)