from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ItemTypeViewSet,
    ItemViewSet,
    ReviewViewSet,
    SearchHistoryViewSet,
    ViewHistoryViewSet,
    FavoriteCategoryViewSet,
    MyItemsView,
)

router = DefaultRouter()

router.register(r'category', CategoryViewSet, basename='category')
router.register(r'type', ItemTypeViewSet, basename='type')
router.register(r'item', ItemViewSet, basename='item')
router.register(r'search-history', SearchHistoryViewSet, basename='search-history')
router.register(r'view-history', ViewHistoryViewSet, basename='view-history')
router.register(r'favorite-categories', FavoriteCategoryViewSet, basename='favorite-category')


urlpatterns = [
    path('item/my/', MyItemsView.as_view(), name='list-my-items'),

    path('', include(router.urls)),
    
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
]