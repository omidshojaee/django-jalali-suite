"""Model fields that store Gregorian values and expose Jalali ones.

The database column is an ordinary ``date``/``timestamp``; only the Python value
differs. A field descriptor normalises *every* assignment (constructor,
``default=``, ``auto_now``, forms, ``refresh_from_db``) to a ``jdatetime``
object, so an instance attribute has the same type whether it was just created
or loaded from the database.
"""

import datetime as dt
import warnings

import jdatetime
from django.conf import settings
from django.core import exceptions
from django.db import models
from django.db.models.functions import TruncDate
from django.db.models.query_utils import DeferredAttribute
from django.utils import timezone

from .forms import JalaliDateField as JalaliDateFormField
from .forms import SplitJalaliDateTimeField
from .lookups import register_lookups
from .utils import to_gregorian_value, to_jalali, to_jalali_datetime


def _coerce_date(value):
    if value is None:
        return None
    try:
        return to_jalali(value)
    except (TypeError, ValueError):
        return value  # leave it for full_clean() to report


def _coerce_datetime(value):
    """Convert ``value`` to a jdatetime.datetime; raise ValueError/TypeError."""
    if value is None:
        return None
    if isinstance(value, jdatetime.datetime):
        return to_jalali_datetime(value)
    if isinstance(value, jdatetime.date):
        value = value.togregorian()
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        # Like Django, a bare date means midnight.
        value = dt.datetime.combine(value, dt.time())
    try:
        return to_jalali_datetime(value)
    except ValueError:
        if isinstance(value, str):
            # Date-only strings mean midnight, as in Django's DateTimeField.
            midnight = dt.datetime.combine(to_jalali(value).togregorian(), dt.time())
            return to_jalali_datetime(midnight)
        raise


class _CoercingDescriptor(DeferredAttribute):
    def __set__(self, instance, value):
        instance.__dict__[self.field.attname] = self.field.coerce(value)


class JalaliDateField(models.DateField):
    description = "Jalali date"
    descriptor_class = _CoercingDescriptor

    def coerce(self, value):
        return _coerce_date(value)

    def from_db_value(self, value, expression, connection):
        return None if value is None else to_jalali(value)

    def to_python(self, value):
        if value is None:
            return None
        try:
            return to_jalali(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            )

    def get_prep_value(self, value):
        value = super(models.DateField, self).get_prep_value(value)
        return to_gregorian_value(self.to_python(value))

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return "" if value is None else to_gregorian_value(value).isoformat()

    def formfield(self, **kwargs):
        # ModelAdmin supplies a default form_class through formfield_overrides.
        # Replace it so the Jalali parser and widget stay in use.
        kwargs["form_class"] = JalaliDateFormField
        return super().formfield(**kwargs)


class JalaliDateTimeField(models.DateTimeField):
    description = "Jalali datetime"
    descriptor_class = _CoercingDescriptor

    def coerce(self, value):
        try:
            return _coerce_datetime(value)
        except (TypeError, ValueError):
            return value  # leave it for full_clean() to report

    def from_db_value(self, value, expression, connection):
        return None if value is None else to_jalali_datetime(value)

    def to_python(self, value):
        try:
            return _coerce_datetime(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            )

    def get_prep_value(self, value):
        value = super(models.DateTimeField, self).get_prep_value(value)
        value = self.to_python(value)
        if value is None:
            return None
        value = value.togregorian()
        if settings.USE_TZ and timezone.is_naive(value):
            # Same fallback (and warning) as Django's own DateTimeField.
            warnings.warn(
                "DateTimeField %s.%s received a naive datetime (%s) while time "
                "zone support is active."
                % (self.model.__name__, self.name, value),
                RuntimeWarning,
            )
            value = timezone.make_aware(value, timezone.get_default_timezone())
        return value

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return "" if value is None else to_gregorian_value(value).isoformat()

    def formfield(self, **kwargs):
        kwargs["form_class"] = SplitJalaliDateTimeField
        return super().formfield(**kwargs)


class JalaliTruncDate(TruncDate):
    """``datetime_field__date`` that yields a Jalali date, so Jalali values and
    ``__year`` work on the result (``at__date="1403-01-01"``, ``at__date__year=1403``).
    The date is taken in the current time zone, like Django's own ``__date``."""

    output_field = JalaliDateField()


register_lookups(JalaliDateField)
register_lookups(JalaliDateTimeField)
JalaliDateTimeField.register_lookup(JalaliTruncDate)

# Names used by django-jalali, so migrating projects need fewer edits. The
# ``jManager`` / ``jQuerySet`` of django-jalali only existed to make ``__year`` and
# ``__date`` work; the lookups here need no special manager, so these are the
# plain Django classes.
jDateField = JalaliDateField
jDateTimeField = JalaliDateTimeField
jManager = models.Manager
jQuerySet = models.QuerySet
