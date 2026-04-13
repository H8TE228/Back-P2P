from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ItemTypeViewSet,
    ItemViewSet,
    TransactionViewSet,
    ReviewViewSet,
    SearchHistoryViewSet,
    ViewHistoryViewSet,
)

router = DefaultRouter()

router.register(r'category', CategoryViewSet, basename='category')
router.register(r'type', ItemTypeViewSet, basename='type')
router.register(r'item', ItemViewSet, basename='item')


urlpatterns = [
    path('', include(router.urls)),
    
    path('transactions/<int:item_id>/', TransactionViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='transaction-list-by-item'),
    
    path('transactions/<int:item_id>/<int:pk>/', TransactionViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='transaction-detail-by-item'),

    path('reviews/<int:item_id>/', ReviewViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='review-list-by-item'),
    
    path('reviews/<int:item_id>/<int:pk>/', ReviewViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='review-detail-by-item'),

    path('search-history/<int:user_id>/', SearchHistoryViewSet.as_view({
        'get': 'list',
    }), name='search-history-list'),

    path('view-history/<int:user_id>/', ViewHistoryViewSet.as_view({
        'get': 'list',
    }), name='view-history-list'),
]