"""Django REST Framework fields for Jalali values.

Input is Jalali (digits may be Persian or Arabic-Indic) and is cleaned to
standard Gregorian ``date``/aware ``datetime`` objects; output is Jalali ISO
text. ISO-like strings are read as Jalali when the year is below 1700 and as
Gregorian otherwise, so a client that sends ``2024-03-20`` is never silently
misread as the year 2024 of the Jalali calendar.
"""

from rest_framework import serializers

from .models import JalaliDateField as ModelJalaliDateField
from .models import JalaliDateTimeField as ModelJalaliDateTimeField
from .utils import (
    isoformat_jalali,
    normalize_digits,
    to_jalali,
    to_jalali_datetime,
)


class JalaliDateSerializerField(serializers.Field):
    default_error_messages = {
        "invalid": "Enter a valid Jalali date in YYYY-MM-DD format."
    }

    def to_internal_value(self, data):
        try:
            return to_jalali(normalize_digits(str(data))).togregorian()
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, value):
        if value in (None, ""):
            return value
        return isoformat_jalali(to_jalali(value))


class JalaliDateTimeSerializerField(serializers.Field):
    default_error_messages = {
        "invalid": "Enter a valid Jalali datetime in YYYY-MM-DDTHH:MM[:SS] format."
    }

    def to_internal_value(self, data):
        try:
            return to_jalali_datetime(normalize_digits(str(data))).togregorian()
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, value):
        if value in (None, ""):
            return value
        return isoformat_jalali(value)


class JalaliModelSerializer(serializers.ModelSerializer):
    """ModelSerializer with automatic fields for Jalali model fields."""

    serializer_field_mapping = (
        serializers.ModelSerializer.serializer_field_mapping.copy()
    )
    serializer_field_mapping[ModelJalaliDateField] = JalaliDateSerializerField
    serializer_field_mapping[ModelJalaliDateTimeField] = JalaliDateTimeSerializerField


# Names used by django-jalali (django_jalali.serializers.serializerfield).
JDateField = JalaliDateSerializerField
JDateTimeField = JalaliDateTimeSerializerField

__all__ = [
    "JalaliDateSerializerField",
    "JalaliDateTimeSerializerField",
    "JalaliModelSerializer",
]
