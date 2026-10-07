import datetime as dt

import jdatetime
from django import template
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from ..query import jalali_dates
from ..utils import format_jalali, to_farsi_digits, uses_farsi_digits

register = template.Library()

_DATE_TYPES = (dt.date, jdatetime.date)  # datetimes are subclasses of these


@register.filter(name="jalali")
def jalali(value, fmt=None):
    if value in (None, ""):
        return "-"
    return format_jalali(value, fmt)


# django-jalali-date's name for the same filter (renders "-" for empty values).
register.filter(name="to_jalali")(jalali)


@register.filter(name="jformat")
def jformat(value, fmt=None):
    """django-jalali's filter: like ``jalali`` but renders "" for empty values."""
    if value in (None, ""):
        return ""
    return format_jalali(value, fmt)


@register.filter
def jalali_digits(value, digits=None):
    if value in (None, ""):
        return "-"
    return format_jalali(value, digits=digits)


@register.simple_tag
def jalali_now(fmt=None):
    now = timezone.localtime() if settings.USE_TZ else dt.datetime.now()
    return format_jalali(now, fmt)


@register.simple_tag
def jalali_date(value, fmt=None, digits=None):
    if value in (None, "") or not isinstance(value, _DATE_TYPES):
        return "-"
    return format_jalali(value, fmt, digits)


@register.inclusion_tag("admin/date_hierarchy.html")
def jalali_date_hierarchy(cl):
    """Admin ``date_hierarchy`` drill-down by Jalali year, month and day.

    Falls back to Django's own tag for fields it does not handle (related paths,
    or admins without :class:`jalali_suite.admin.JalaliDateAdminMixin`).
    """
    field = cl._jalali_hierarchy_field() if hasattr(cl, "_jalali_hierarchy_field") else None
    if field is None:
        from django.contrib.admin.templatetags.admin_list import date_hierarchy

        return date_hierarchy(cl) or {}

    name = cl.date_hierarchy
    year_field, month_field, day_field = (f"{name}__{part}" for part in ("year", "month", "day"))
    year = cl.params.get(year_field)
    month = cl.params.get(month_field)
    day = cl.params.get(day_field)
    dates = jalali_dates(cl.queryset, name, "day")

    def link(filters):
        return cl.get_query_string(filters, [f"{name}__"])

    def number(value):
        return to_farsi_digits(value) if uses_farsi_digits() else str(value)

    if not (year or month or day) and dates:
        # Start at the deepest level that still has something to choose from.
        first, last = dates[0], dates[-1]
        if first.year == last.year:
            year = first.year
            if first.month == last.month:
                month = first.month

    context = {"show": True, "field_name": field.verbose_name}
    if year and month and day:
        chosen = jdatetime.date(int(year), int(month), int(day))
        context["back"] = {
            "link": link({year_field: year, month_field: month}),
            "title": format_jalali(chosen, "%B %Y"),
        }
        context["choices"] = [{"title": format_jalali(chosen, "%d %B")}]
    elif year and month:
        context["back"] = {"link": link({year_field: year}), "title": number(year)}
        context["choices"] = [
            {
                "link": link({year_field: year, month_field: month, day_field: item.day}),
                "title": format_jalali(item, "%d %B"),
            }
            for item in dates
            if (item.year, item.month) == (int(year), int(month))
        ]
    elif year:
        months = sorted({(item.year, item.month) for item in dates if item.year == int(year)})
        context["back"] = {"link": link({}), "title": _("All dates")}
        context["choices"] = [
            {
                "link": link({year_field: year, month_field: month_number}),
                "title": format_jalali(jdatetime.date(year_number, month_number, 1), "%B %Y"),
            }
            for year_number, month_number in months
        ]
    else:
        context["back"] = None
        context["choices"] = [
            {"link": link({year_field: str(year_number)}), "title": number(year_number)}
            for year_number in sorted({item.year for item in dates})
        ]
    return context
