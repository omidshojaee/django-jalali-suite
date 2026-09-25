from django import forms
from django.contrib import admin
from django.contrib.admin import FieldListFilter
from django.core.exceptions import FieldDoesNotExist
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .forms import JalaliDateField
from .models import JalaliDateField as ModelJalaliDateField
from .models import JalaliDateTimeField
from .utils import format_jalali
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
            # Don't forward attrs from the widget Django's own
            # formfield_overrides handed back (plain AdminDateWidget): its
            # "vDateField" class would re-attach Django's native calendar/
            # "Today" shortcut, which writes a raw Gregorian date straight
            # into a Jalali field, bypassing our widget entirely.
            formfield.widget = AdminJalaliDateWidget()
        elif isinstance(db_field, JalaliDateTimeField) and formfield:
            formfield.widget = AdminJalaliSplitDateTimeWidget(
                attrs=formfield.widget.attrs
            )
        return formfield

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj)

    def get_list_display(self, request):
        fields = list(super().get_list_display(request))
        for index, name in enumerate(fields):
            try:
                field = self.opts.get_field(name)
            except (FieldDoesNotExist, TypeError):
                continue
            if isinstance(field, (ModelJalaliDateField, JalaliDateTimeField)):
                method_name = f"get_jalali_{name}"

                def display_value(obj, field_name=name):
                    value = getattr(obj, field_name)
                    if value is None:
                        return None
                    # Isolate from the surrounding page direction: admin
                    # skins are often LTR, and a format mixing "/" with
                    # RTL month/weekday/AM-PM words scrambles under the
                    # bidi algorithm without this.
                    return format_html("<bdi>{}</bdi>", format_jalali(value))

                display_value.short_description = field.verbose_name
                setattr(
                    self,
                    method_name,
                    display_value,
                )
                fields[index] = method_name
        return fields


class JalaliDateModelAdmin(JalaliDateAdminMixin, admin.ModelAdmin):
    pass
