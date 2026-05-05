from .models import SearchHistory


# Параметры запроса, которые мы считаем "осмысленным поиском".
# Если ни один из них в URL не присутствует — историю не пишем.
SEARCH_PARAM_KEYS = (
    'search',
    'category', 'category_name',
    'type', 'type_name',
    'min_price', 'max_price',
    'status',
    'created_at__gte', 'created_at__lte',
    'owner',
)


def log_item_search(user, query_params):
    """
    Записывает или обновляет запись в SearchHistory для пользователя.

    user           — request.user, должен быть аутентифицирован.
    query_params   — request.query_params (DRF) либо обычный dict.

    Возвращает (entry, created):
      - SearchHistory или None (если поиск пустой/аноним),
      - bool: True если создана новая запись, False если обновлена существующая.
    """
    if not user or not user.is_authenticated:
        return None, False

    raw = {}
    for key in SEARCH_PARAM_KEYS:
        if key in query_params:
            value = query_params.get(key)
            if value is None or value == '':
                continue
            raw[key] = value

    if not raw:
        return None, False

    query_text = (raw.pop('search', '') or '').strip()[:255]
    filters = raw  # всё остальное

    existing = SearchHistory.objects.filter(
        user=user,
        query_text=query_text,
        filters=filters,
    ).first()

    if existing:
        existing.save(update_fields=['last_searched_at'])
        return existing, False

    entry = SearchHistory.objects.create(
        user=user,
        query_text=query_text,
        filters=filters,
    )
    return entry, True