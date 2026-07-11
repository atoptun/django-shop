from django.core.exceptions import PermissionDenied


class StaffOnlyMiddleware:
    def resolve(self, next, root, info, **kwargs):
        if root is None:
            user = info.context.user
            if not user.is_authenticated or not user.is_staff:
                raise PermissionDenied()
        return next(root, info, **kwargs)
