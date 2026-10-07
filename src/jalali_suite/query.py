"""Queryset helpers for the Jalali calendar."""

import jdatetime
from django.contrib.admin.utils import get_fields_from_path
from django.db import models

from .utils import to_jalali

_TRUNCATIONS = {
    "year": lambda d: jdatetime.date(d.year, 1, 1),
    "month": lambda d: jdatetime.date(d.year, d.month, 1),
    "day": lambda d: d,
}


def jalali_dates(queryset, field_name, kind="day"):
    """Distinct Jalali dates of a date/datetime field, like ``QuerySet.dates()``.

    ``QuerySet.dates()`` / ``.datetimes()`` truncate on the *Gregorian* calendar
    (a Jalali ``kind="year"`` would return 2024-01-01, not Nowruz). This returns a
    sorted list of ``jdatetime.date`` truncated to ``kind`` (``"year"``,
    ``"month"`` or ``"day"``). Datetimes are read in the current time zone.
    """
    try:
        truncate = _TRUNCATIONS[kind]
    except KeyError:
        raise ValueError("kind must be 'year', 'month' or 'day'") from None
    field = get_fields_from_path(queryset.model, field_name)[-1]
    lookup = f"{field_name}__date" if isinstance(field, models.DateTimeField) else field_name
    values = queryset.order_by().values_list(lookup, flat=True).distinct()
    return sorted({truncate(to_jalali(value)) for value in values if value is not None})
