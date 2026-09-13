from rest_framework import serializers

from .utils import JalaliDate, JalaliDateTime, normalize_digits


class JalaliDateSerializerField(serializers.Field):
    def to_internal_value(self, data):
        from .forms import JalaliDateField

        return JalaliDateField().clean(normalize_digits(str(data)))

    def to_representation(self, value):
        if isinstance(value, JalaliDate):
            return value.isoformat
        return value


class JalaliDateTimeSerializerField(serializers.Field):
    def to_internal_value(self, data):
        from .forms import JalaliDateTimeField

        return JalaliDateTimeField().clean(normalize_digits(str(data)))

    def to_representation(self, value):
        if isinstance(value, JalaliDateTime):
            return value.isoformat
        return value