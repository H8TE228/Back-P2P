import django_filters
from .models import Item

class ItemFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    category = django_filters.NumberFilter(field_name='type__category_id')
    category_name = django_filters.CharFilter(
        field_name='type__category__name',
        lookup_expr='iexact',
    )
    type = django_filters.NumberFilter(field_name='type_id')
    type_name = django_filters.CharFilter(
        field_name='type__name',
        lookup_expr='iexact',
    )
    owner = django_filters.NumberFilter(field_name='owner_id')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Item
        fields = {
            'status': ['exact'],
            'created_at': ['gte', 'lte'],
        }


    def filter_search(self, queryset, name, value):
        return queryset.filter(
            name__icontains=value) | queryset.filter(
            description__icontains=value
        )