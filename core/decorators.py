from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("User not authenticated")

            if request.user.role.name not in allowed_roles:
                raise PermissionDenied("Access denied")

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
