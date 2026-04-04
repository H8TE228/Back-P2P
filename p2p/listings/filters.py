import django_filters
from .models import Listing

class ListingFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    category_slug = django_filters.CharFilter(field_name='category__slug')
    search = django_filters.CharFilter(method='filter_search')
    owner_username = django_filters.CharFilter(field_name='owner__username')

    class Meta:
        model = Listing
        fields = {
            'status': ['exact'],
            'category': ['exact'],
            'created_at': ['gte', 'lte'],
        }

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            title__icontains=value) | queryset.filter(
            description__icontains=value
        )