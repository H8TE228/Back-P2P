from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ItemFilter


from .models import (
    Category, ItemType, Item, ItemImage, 
    SearchHistory, ViewHistory, FavoriteCategory,
    Review, 
)
from .serializers import (
    CategorySerializer, ItemTypeSerializer, ItemSerializer, ItemImageSerializer,
    SearchHistorySerializer, ViewHistorySerializer, FavoriteCategorySerializer,
    ReviewSerializer, 
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


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


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ItemFilter

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
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ItemImageViewSet(viewsets.ModelViewSet):
    queryset = ItemImage.objects.all()
    serializer_class = ItemImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Review.objects.all()
        item_id = self.request.query_params.get('item_id', None)
        recipient_id = self.request.query_params.get('recipient_id', None)
        transaction_id = self.request.query_params.get('transaction_id', None)

        if item_id:
            queryset = queryset.filter(item_id=item_id)
        if recipient_id:
            queryset = queryset.filter(recipient_id=recipient_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        reviews = Review.objects.filter(author=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def received_reviews(self, request):
        reviews = Review.objects.filter(recipient=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def transaction_reviews(self, request, transaction_id=None):
        """Получить все отзывы для конкретной транзакции (от арендатора и арендодателя)"""
        transaction_id = self.request.query_params.get('transaction_id')
        if not transaction_id:
            return Response({'error': 'transaction_id required'}, status=status.HTTP_400_BAD_REQUEST)
        reviews = Review.objects.filter(transaction_id=transaction_id)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

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

    @action(detail=False, methods=['post'])
    def log_search(self, request):
        """Логгирование поискового запроса"""
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

    @action(detail=False, methods=['post'])
    def log_view(self, request):
        """Логгирование просмотра предмета"""
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FavoriteCategoryViewSet(viewsets.ModelViewSet):
    queryset = FavoriteCategory.objects.all()
    serializer_class = FavoriteCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return FavoriteCategory.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)