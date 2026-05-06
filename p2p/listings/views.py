from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg
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
)
from .serializers import (
    CategorySerializer, ItemTypeSerializer, ItemSerializer, ItemImageSerializer, NotificationSerializer,
    SearchHistorySerializer, ViewHistorySerializer, FavoriteCategorySerializer,
    FavoriteItemSerializer,
    ReviewSerializer, ItemDetailSerializer
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
            
        if self.action == 'retrieve':
            return queryset.select_related('owner').all()
        
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