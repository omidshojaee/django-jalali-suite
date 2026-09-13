"""Django REST Framework fields for Jalali model values."""

from rest_framework import serializers

from .models import JalaliDateField as ModelJalaliDateField
from .models import JalaliDateTimeField as ModelJalaliDateTimeField
from .utils import (
    JalaliDate,
    JalaliDateTime,
    normalize_digits,
    to_jalali,
    to_jalali_datetime,
)


class JalaliDateSerializerField(serializers.Field):
    def to_internal_value(self, data):
        from .forms import JalaliDateField

        try:
            return JalaliDateField().clean(normalize_digits(str(data)))
        except Exception as error:
            raise serializers.ValidationError(str(error)) from error

    def to_representation(self, value):
        if isinstance(value, JalaliDate):
            return value.isoformat
        if value in (None, ""):
            return value
        return to_jalali(value).isoformat


class JalaliDateTimeSerializerField(serializers.Field):
    def to_internal_value(self, data):
        from .forms import JalaliDateTimeField

        try:
            return JalaliDateTimeField().clean(normalize_digits(str(data)))
        except Exception as error:
            raise serializers.ValidationError(str(error)) from error

    def to_representation(self, value):
        if isinstance(value, JalaliDateTime):
            return value.isoformat
        if value in (None, ""):
            return value
        return to_jalali_datetime(value).isoformat


class JalaliModelSerializer(serializers.ModelSerializer):
    """ModelSerializer with automatic fields for Jalali model fields."""

    serializer_field_mapping = (
        serializers.ModelSerializer.serializer_field_mapping.copy()
    )
    serializer_field_mapping[ModelJalaliDateField] = JalaliDateSerializerField
    serializer_field_mapping[ModelJalaliDateTimeField] = JalaliDateTimeSerializerField


__all__ = [
    "JalaliDateSerializerField",
    "JalaliDateTimeSerializerField",
    "JalaliModelSerializer",
]
