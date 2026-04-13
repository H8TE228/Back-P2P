from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Проверка владельца
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'author'):
            return obj.author == request.user
        if hasattr(obj, 'user'): # Для историй
            return obj.user == request.user
            
        return False

class IsRenterOrOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user or obj.renter == request.user

class IsUserInPath(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_id = view.kwargs.get('user_id')
        
        if user_id is None:
            return False
            
        return int(user_id) == request.user.id