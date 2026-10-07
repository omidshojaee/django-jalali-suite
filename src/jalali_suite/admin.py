import datetime as dt

import jdatetime
from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import DateFieldListFilter, FieldListFilter
from django.contrib.admin.options import IncorrectLookupParameters
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.html import format_html

from .forms import JalaliDateField, SplitJalaliDateTimeField
from .models import JalaliDateField as ModelJalaliDateField
from .models import JalaliDateTimeField as ModelJalaliDateTimeField
from .settings import jalali_settings
from .utils import _make_aware, format_jalali, jalali_datetime_range, jalali_range
from .widgets import AdminJalaliDateWidget, AdminJalaliSplitDateTimeWidget


class JalaliDateFieldListFilter(DateFieldListFilter):
    """Django's date filter with Today / This month / This year in the Jalali calendar."""

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)

        now = timezone.localtime() if settings.USE_TZ else dt.datetime.now()
        jtoday = jdatetime.date.fromgregorian(date=now.date())
        is_datetime = isinstance(field, models.DateTimeField)

        def bound(day):
            return _make_aware(dt.datetime.combine(day, dt.time())) if is_datetime else day

        today = jtoday.togregorian()
        tomorrow = today + dt.timedelta(days=1)
        month_start, next_month = jalali_range(jtoday.year, jtoday.month)
        year_start, next_year = jalali_range(jtoday.year)

        since, until = self.lookup_kwarg_since, self.lookup_kwarg_until
        # Django's links: Any date, Today, Past 7 days, This month, This year,
        # then (for nullable fields) No date / Has date, which stay as they are.
        links = list(self.links)
        replacements = {
            1: (bound(today), bound(tomorrow)),
            2: (bound(today - dt.timedelta(days=7)), bound(tomorrow)),
            3: (bound(month_start), bound(next_month)),
            4: (bound(year_start), bound(next_year)),
        }
        for index, (start, end) in replacements.items():
            links[index] = (links[index][0], {since: start, until: end})
        self.links = tuple(links)


FieldListFilter.register(
    lambda f: isinstance(f, (ModelJalaliDateField, ModelJalaliDateTimeField)),
    JalaliDateFieldListFilter,
    take_priority=True,
)


def _is_date_field(db_field):
    return isinstance(db_field, models.DateField)  # includes DateTimeField


class _JalaliChangeListMixin:
    """Make ``date_hierarchy`` drill-down use the Jalali calendar.

    Django turns ``?field__year=Y&field__month=M`` into Gregorian bounds, which
    would silently filter the wrong dates for Jalali numbers. Here the same
    parameters become Jalali bounds before Django looks at them.
    """

    def _jalali_hierarchy_field(self):
        name = self.date_hierarchy
        model_admin = self.model_admin
        if not name or "__" in name or not getattr(model_admin, "jalali_date_hierarchy", False):
            return None
        try:
            field = self.lookup_opts.get_field(name)
        except FieldDoesNotExist:
            return None
        return field if model_admin._wants_jalali(field) else None

    def _with_jalali_bounds(self, params, field):
        name = self.date_hierarchy
        if params.get(f"{name}__year") is None:
            return params
        params = dict(params)
        year = params.pop(f"{name}__year")
        month = params.pop(f"{name}__month", None)
        day = params.pop(f"{name}__day", None)
        make_range = (
            jalali_datetime_range
            if isinstance(field, models.DateTimeField)
            else jalali_range
        )
        try:
            month_number = int(month[-1]) if month else None
            day_number = int(day[-1]) if day else None
            start, end = make_range(
                int(year[-1]),
                month_number or (1 if day else None),
                day_number,
            )
        except ValueError as exc:
            raise IncorrectLookupParameters(exc) from exc
        params[f"{name}__gte"] = [start]
        params[f"{name}__lt"] = [end]
        return params

    def get_filters(self, request):
        field = self._jalali_hierarchy_field()
        if field is None:
            return super().get_filters(request)
        original = self.filter_params
        self.filter_params = self._with_jalali_bounds(original, field)
        try:
            return super().get_filters(request)
        finally:
            self.filter_params = original


_changelist_classes = {}


def _jalali_changelist_class(base):
    if base not in _changelist_classes:
        _changelist_classes[base] = type(
            f"Jalali{base.__name__}", (_JalaliChangeListMixin, base), {}
        )
    return _changelist_classes[base]


class JalaliDateAdminMixin:
    """Jalali widgets and presentation for a ModelAdmin or inline.

    It acts on the suite's Jalali model fields: Jalali widgets, Jalali list
    columns (still sortable), read-only values, filters and ``date_hierarchy``.
    Plain Django ``DateField``/``DateTimeField`` columns are left alone, since
    they are not declared as Jalali; set
    ``jalali_widgets_for_gregorian_fields = True`` to treat them the same way
    (handy when moving over from django-jalali-date).
    """

    jalali_widgets_for_gregorian_fields = False
    #: Drill down ``date_hierarchy`` by Jalali year, month and day.
    jalali_date_hierarchy = True
    change_list_template = "jalali_suite/admin/change_list.html"

    def get_changelist(self, request, **kwargs):
        changelist = super().get_changelist(request, **kwargs)
        return _jalali_changelist_class(changelist) if self.jalali_date_hierarchy else changelist

    @property
    def media(self):
        media = super().media + forms.Media(
            css={"all": ("jalali_suite/css/jalali-datepicker.css",)},
            js=("jalali_suite/js/jalali-datepicker.js",),
        )
        return media + forms.Media(css={"all": ("jalali_suite/css/vazirmatn.css",)})

    def _wants_jalali(self, db_field):
        if not _is_date_field(db_field) or db_field.choices:
            return False
        if isinstance(db_field, (ModelJalaliDateField, ModelJalaliDateTimeField)):
            return True
        return self.jalali_widgets_for_gregorian_fields

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if not self._wants_jalali(db_field):
            return super().formfield_for_dbfield(db_field, request, **kwargs)
        # Skip Django's formfield_overrides: its plain AdminDateWidget carries
        # the "vDateField" class, which would re-attach Django's own calendar and
        # "Today" shortcut and write a raw Gregorian date into a Jalali field.
        kwargs.pop("widget", None)
        kwargs.pop("form_class", None)
        if isinstance(db_field, models.DateTimeField):
            return db_field.formfield(
                form_class=SplitJalaliDateTimeField,
                widget=AdminJalaliSplitDateTimeWidget,
                **kwargs,
            )
        return db_field.formfield(
            form_class=JalaliDateField, widget=AdminJalaliDateWidget, **kwargs
        )

    def _auto_convert(self):
        return jalali_settings.get("LIST_DISPLAY_AUTO_CONVERT")

    def _jalali_column_for(self, name):
        """The Jalali display callable for a date field name, else ``None``.

        Callables are cached per admin instance: Django matches readonly fields
        in a fieldset by identity, so every call must return the same object.
        """
        if not isinstance(name, str):
            return None
        try:
            field = self.opts.get_field(name)
        except (FieldDoesNotExist, TypeError, AttributeError):
            return None
        if not self._wants_jalali(field):
            return None
        cache = self.__dict__.setdefault("_jalali_columns", {})
        if name not in cache:
            cache[name] = self._jalali_column(field)
        return cache[name]

    def get_list_display(self, request):
        fields = list(super().get_list_display(request))
        if not self._auto_convert():
            return fields
        return [self._jalali_column_for(name) or name for name in fields]

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not self._auto_convert():
            return readonly
        return [self._jalali_column_for(name) or name for name in readonly]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not self._auto_convert():
            return fieldsets
        # Readonly date fields were swapped for Jalali display callables above;
        # point explicitly listed names in the layout at the same callables.
        names = {
            name
            for name in super().get_readonly_fields(request, obj)
            if isinstance(name, str)
        }

        def swap(item):
            if isinstance(item, (list, tuple)):
                return type(item)(swap(part) for part in item)
            return (self._jalali_column_for(item) or item) if item in names else item

        return [
            (title, {**options, "fields": swap(options.get("fields", ()))})
            for title, options in fieldsets
        ]

    @staticmethod
    def _jalali_column(field):
        @admin.display(description=field.verbose_name, ordering=field.name)
        def column(obj):
            value = getattr(obj, field.name)
            if value is None:
                return None
            # Isolate from the surrounding page direction: admin skins are
            # often LTR, and a format mixing "/" with RTL month/weekday/AM-PM
            # words scrambles under the bidi algorithm without this.
            return format_html("<bdi>{}</bdi>", format_jalali(value))

        column.__name__ = f"jalali_{field.name}"
        return column


class JalaliDateModelAdmin(JalaliDateAdminMixin, admin.ModelAdmin):
    pass


class JalaliDateTabularInline(JalaliDateAdminMixin, admin.TabularInline):
    pass


class JalaliDateStackedInline(JalaliDateAdminMixin, admin.StackedInline):
    pass


# Names used by django-jalali ...
JDateFieldListFilter = JalaliDateFieldListFilter

# ... and by django-jalali-date, so migrating projects need fewer edits.
ModelAdminJalaliMixin = JalaliDateAdminMixin
TabularInlineJalaliMixin = JalaliDateAdminMixin
StackedInlineJalaliMixin = JalaliDateAdminMixin
