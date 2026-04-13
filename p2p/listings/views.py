from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from .models import (
    Category, ItemType, Item, ItemImage, 
    Transaction, Review, SearchHistory, ViewHistory, FavoriteCategory
)
from .serializers import (
    CategorySerializer, ItemTypeSerializer, ItemSerializer, ItemImageSerializer,
    TransactionSerializer, ReviewSerializer, SearchHistorySerializer, 
    ViewHistorySerializer, FavoriteCategorySerializer
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


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(Q(owner=user) | Q(renter=user))

    def perform_create(self, serializer):
        item = serializer.validated_data.get('item')
        if item:
            serializer.save(owner=item.owner, renter=self.request.user)
        else:
            serializer.save(renter=self.request.user)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Review.objects.all()
        item_id = self.request.query_params.get('item_id', None)
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class SearchHistoryViewSet(viewsets.ModelViewSet):
    queryset = SearchHistory.objects.all()
    serializer_class = SearchHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_superuser:
            return SearchHistory.objects.filter(user=user)
        
        user_id = self.kwargs.get('user_id') # Если маршрут настроен так
        if user_id:
            return SearchHistory.objects.filter(user_id=user_id)
        return SearchHistory.objects.all()

    @action(detail=False, methods=['post'])
    def add(self, request):
        serializer = self.get_serializer(data=request.data)
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
        if not user.is_superuser:
            return ViewHistory.objects.filter(user=user)
        return ViewHistory.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FavoriteCategoryViewSet(viewsets.ModelViewSet):
    queryset = FavoriteCategory.objects.all()
    serializer_class = FavoriteCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return FavoriteCategory.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)