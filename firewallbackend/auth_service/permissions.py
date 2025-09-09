from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée pour permettre la lecture à tous les utilisateurs
    mais la modification uniquement aux administrateurs.
    """
    
    def has_permission(self, request, view):
        # Permettre la lecture à tous les utilisateurs authentifiés
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Permettre la modification uniquement aux administrateurs
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission personnalisée pour permettre l'accès au propriétaire de l'objet
    ou aux administrateurs.
    """
    
    def has_object_permission(self, request, view, obj):
        # Les administrateurs ont tous les droits
        if request.user and request.user.is_staff:
            return True
        
        # Vérifier si l'utilisateur est le propriétaire de l'objet
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée pour permettre la lecture à tous
    mais la modification uniquement aux utilisateurs authentifiés.
    """
    
    def has_permission(self, request, view):
        # Permettre la lecture à tous
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permettre la modification uniquement aux utilisateurs authentifiés
        return request.user and request.user.is_authenticated
