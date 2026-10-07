"""Jalali-aware lookups for the model fields.

``__year`` is answered with a half-open Gregorian range, so it stays portable
across databases and keeps indexes usable. ``__month``, ``__day`` and
``__quarter`` cannot be expressed that way without database-specific calendar
functions, and silently returning *Gregorian* months would be wrong, so they
raise instead. Use :func:`jalali_suite.utils.jalali_range` (or
``jalali_datetime_range``) with ``__gte``/``__lt`` for those.
"""

import datetime as dt

from django.core.exceptions import FieldError
from django.db import models
from django.db.models import IntegerField, Transform
from django.db.models.lookups import YearExact, YearGt, YearGte, YearLt, YearLte

from .utils import jalali_datetime_range, jalali_range


class JalaliYear(Transform):
    lookup_name = "year"
    output_field = IntegerField()

    def as_sql(self, compiler, connection):
        raise FieldError(
            "Jalali 'year' can only be compared to an integer, e.g. "
            "field__year=1403 or field__year__gte=1403; it cannot be used as "
            "an expression."
        )


class _JalaliYearBounds:
    def year_lookup_bounds(self, connection, year):
        output_field = self.lhs.lhs.output_field
        if isinstance(output_field, models.DateTimeField):
            start, end = jalali_datetime_range(year)
            end -= dt.timedelta(microseconds=1)
            adapt = connection.ops.adapt_datetimefield_value
        else:
            start, end = jalali_range(year)
            end -= dt.timedelta(days=1)
            adapt = connection.ops.adapt_datefield_value
        return [adapt(start), adapt(end)]


class JalaliYearExact(_JalaliYearBounds, YearExact):
    pass


class JalaliYearGt(_JalaliYearBounds, YearGt):
    pass


class JalaliYearGte(_JalaliYearBounds, YearGte):
    pass


class JalaliYearLt(_JalaliYearBounds, YearLt):
    pass


class JalaliYearLte(_JalaliYearBounds, YearLte):
    pass


for _lookup in (
    JalaliYearExact,
    JalaliYearGt,
    JalaliYearGte,
    JalaliYearLt,
    JalaliYearLte,
):
    JalaliYear.register_lookup(_lookup)


def _unsupported(name):
    class Unsupported(Transform):
        lookup_name = name

        def __init__(self, *args, **kwargs):
            raise FieldError(
                f"'{name}' lookups are not supported on Jalali fields (they would "
                "silently use the Gregorian calendar). Filter with "
                "field__gte/field__lt and jalali_suite.utils.jalali_range() "
                "or jalali_datetime_range() instead."
            )

    Unsupported.__name__ = f"JalaliUnsupported_{name}"
    return Unsupported


def register_lookups(field_class):
    field_class.register_lookup(JalaliYear)
    for name in ("month", "day", "quarter"):
        field_class.register_lookup(_unsupported(name))
