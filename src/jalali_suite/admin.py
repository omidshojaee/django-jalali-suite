from django import forms
from django.contrib import admin
from django.contrib.admin import FieldListFilter
from django.core.exceptions import FieldDoesNotExist
from django.utils.translation import gettext_lazy as _

from .forms import JalaliDateField
from .models import JalaliDateField as ModelJalaliDateField
from .models import JalaliDateTimeField
from .settings import jalali_settings
from .utils import format_jalali, to_gregorian
from .widgets import AdminJalaliDateWidget, AdminJalaliSplitDateTimeWidget


class JalaliDateFieldListFilter(FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field_path = field_path
        self.lookup_kwarg = f"{field_path}__gte"
        self.params = params
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg]

    def choices(self, changelist):
        current = self.params.get(self.lookup_kwarg)
        yield {
            "selected": not current,
            "query_string": changelist.get_query_string({}, [self.lookup_kwarg]),
            "display": _("Any date"),
        }
        if current:
            yield {
                "selected": True,
                "query_string": changelist.get_query_string({}, []),
                "display": current,
            }


class JalaliDateAdminMixin:
    """Opt-in Jalali widgets and presentation for one ModelAdmin."""

    @property
    def media(self):
        media = super().media + forms.Media(
            css={"all": ("jalali_suite/css/jalali-datepicker.css",)},
            js=("jalali_suite/js/jalali-datepicker.js",),
        )
        return media + forms.Media(css={"all": ("jalali_suite/css/vazirmatn.css",)})

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, ModelJalaliDateField) and formfield:
            formfield.widget = AdminJalaliDateWidget(attrs=formfield.widget.attrs)
        elif isinstance(db_field, JalaliDateTimeField) and formfield:
            formfield.widget = AdminJalaliSplitDateTimeWidget(
                attrs=formfield.widget.attrs
            )
        return formfield

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj)

    def get_list_display(self, request):
        fields = list(super().get_list_display(request))
        if not jalali_settings.get("ADMIN_AUTO_CONVERT_LIST_DISPLAY"):
            return fields
        for index, name in enumerate(fields):
            try:
                field = self.opts.get_field(name)
            except (FieldDoesNotExist, TypeError):
                continue
            if isinstance(field, (ModelJalaliDateField, JalaliDateTimeField)):
                method_name = f"get_jalali_{name}"
                setattr(
                    self,
                    method_name,
                    lambda obj, field_name=name: format_jalali(
                        getattr(obj, field_name)
                    ),
                )
                fields[index] = method_name
        return fields


class JalaliDateModelAdmin(JalaliDateAdminMixin, admin.ModelAdmin):
    pass
