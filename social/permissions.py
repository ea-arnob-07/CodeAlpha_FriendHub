from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    message = "You do not have permission to change this resource."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, "author", getattr(obj, "user", None))
        return owner == request.user

