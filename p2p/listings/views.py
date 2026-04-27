from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ItemFilter
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from drf_spectacular.utils import extend_schema


from .models import (
    Category, ItemType, Item, ItemImage, 
    SearchHistory, ViewHistory, FavoriteCategory,
    Review, 
)
from .serializers import (
    CategorySerializer, ItemTypeSerializer, ItemSerializer, ItemImageSerializer,
    SearchHistorySerializer, ViewHistorySerializer, FavoriteCategorySerializer,
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
        # Суперпользователь видит все, обычные - только свои
        if user.is_superuser:
            user_id = self.kwargs.get('user_id')
            if user_id:
                return SearchHistory.objects.filter(user_id=user_id)
            return SearchHistory.objects.all()
        return SearchHistory.objects.filter(user=user)

    def perform_create(self, serializer):
        # Автоматически привязываем поиск к текущему пользователю
        serializer.save(user=self.request.user)

    @extend_schema(
        tags=["search history"],
        description="""
            Логгирование поискового запроса
        """
    )
    @action(detail=False, methods=['post'])
    def log_search(self, request):
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["view history"],
    description="""
        CRUD для истории просмотренных пользователем предметов
    """
)
class ViewHistoryViewSet(viewsets.ModelViewSet):
    queryset = ViewHistory.objects.all()
    serializer_class = ViewHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Суперпользователь видит все, обычные - только свои
        if user.is_superuser:
            user_id = self.kwargs.get('user_id')
            if user_id:
                return ViewHistory.objects.filter(user_id=user_id)
            return ViewHistory.objects.all()
        return ViewHistory.objects.filter(user=user)

    def perform_create(self, serializer):
        # Автоматически привязываем просмотр к текущему пользователю
        serializer.save(user=self.request.user)

    @extend_schema(
        tags=["view history"],
        description="""
            Логгирование просмотра предмета
        """
    )
    @action(detail=False, methods=['post'])
    def log_view(self, request):
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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