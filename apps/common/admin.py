from django.db import models
from django_json_widget.widgets import JSONEditorWidget
from safedelete.admin import SafeDeleteAdmin
from unfold.admin import ModelAdmin


class BaseSafeDeleteUnfoldAdmin(ModelAdmin, SafeDeleteAdmin):
    """
    Class that combines the functionality of django-unfold and django-safedelete
    for the Django admin interface.
    It provides a hybrid admin class that allows for soft deletion of objects while
    also providing an enhanced
    user experience with unfoldable sections in the admin interface.
    """

    formfield_overrides = {
        # models.CharField: {
        #     "widget": forms.TextInput(
        #         attrs={
        #             "style": "max-width: 200px;",
        #         }
        #     )
        # },
        # models.DecimalField: {
        #     "widget": forms.NumberInput(
        #         attrs={
        #             "style": "max-width: 150px;",
        #         }
        #     )
        # },
        # models.IntegerField: {
        #     "widget": forms.NumberInput(
        #         attrs={
        #             "style": "max-width: 150px;",
        #         }
        #     )
        # },
        models.JSONField: {
            "widget": JSONEditorWidget(
                attrs={
                    "style": "width: 100%; height: 350px;",
                }
            )
        },
    }

    def log_undeletion(self, request, object, *args, **kwargs):
        try:
            super().log_undeletion(request, object, *args, **kwargs)
        except AttributeError:
            pass

    def get_queryset(self, request):
        return SafeDeleteAdmin.get_queryset(self, request)
