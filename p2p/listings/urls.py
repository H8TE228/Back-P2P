from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ItemTypeViewSet,
    ItemViewSet,
    ItemImageViewSet,
    ReviewViewSet,
    SearchHistoryViewSet,
    ViewHistoryViewSet,
    FavoriteCategoryViewSet,
)

router = DefaultRouter()

router.register(r'category', CategoryViewSet, basename='category')
router.register(r'type', ItemTypeViewSet, basename='type')
router.register(r'item', ItemViewSet, basename='item')
router.register(r'item-images', ItemImageViewSet, basename='item-image')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'search-history', SearchHistoryViewSet, basename='search-history')
router.register(r'view-history', ViewHistoryViewSet, basename='view-history')
router.register(r'favorite-categories', FavoriteCategoryViewSet, basename='favorite-category')


urlpatterns = [
    path('', include(router.urls)),
]