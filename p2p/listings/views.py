from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Category, Listing
from .serializers import CategorySerializer, ListingSerializer
from .filters import ListingFilter

class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD для категорий.
    Доступно всем (только чтение), создание/изменение - только авторизованным.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [SearchFilter]
    search_fields = ['name', 'slug']

class ListingViewSet(viewsets.ModelViewSet):
    """
    CRUD для объявлений.
    - Список: доступен всем
    - Создание: только авторизованным
    - Редактирование/Удаление: только владельцем
    """
    queryset = Listing.objects.select_related('owner', 'category').prefetch_related('images').all()
    serializer_class = ListingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ListingFilter
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at', 'updated_at']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # Автоматически устанавливаем владельца при создании
        serializer.save(owner=self.request.user)

    def get_permissions(self):
        """
        Разрешения зависят от действия:
        - create: требуется авторизация
        - update/partial_update/destroy: только владелец
        """
        if self.action in ['create']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Для действий update/destroy возвращаем только объявления текущего пользователя,
        чтобы проверить права доступа.
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            return Listing.objects.filter(owner=self.request.user)
        return super().get_queryset()