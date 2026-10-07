"""Form fields that accept Jalali input and clean to ordinary Gregorian values.

Cleaned values are standard ``datetime.date`` / aware ``datetime.datetime``
objects, so the fields work with any model field (including plain Django
``DateField``/``DateTimeField``) and with any code that expects standard types.
The Jalali model fields convert them back to Jalali values on assignment.
"""

import datetime as dt

import jdatetime
from django import forms
from django.utils.encoding import force_str

from .utils import (
    _make_aware,
    normalize_digits,
    to_jalali,
    to_jalali_datetime,
)
from .widgets import (
    JalaliDateTimeWidget,
    JalaliDateWidget,
    JalaliSplitDateTimeWidget,
    JalaliTimeWidget,
)


class _ChangeDetectionMixin:
    """Compare initial and submitted values after cleaning both."""

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        try:
            data_value = self.to_python(data)
        except forms.ValidationError:
            return True
        try:
            initial_value = self.to_python(initial)
        except forms.ValidationError:
            initial_value = None
        return initial_value != data_value


class JalaliDateField(_ChangeDetectionMixin, forms.Field):
    widget = JalaliDateWidget
    default_error_messages = {
        "invalid": "Enter a valid Jalali date in YYYY-MM-DD format."
    }

    def __init__(self, *, input_formats=None, **kwargs):
        self.input_formats = input_formats
        super().__init__(**kwargs)

    def to_python(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, (jdatetime.datetime, dt.datetime)):
            return to_jalali(value).togregorian()
        if isinstance(value, jdatetime.date):
            return value.togregorian()
        if isinstance(value, dt.date):
            return value
        text = normalize_digits(force_str(value).strip())
        try:
            for fmt in self.input_formats or ():
                try:
                    return jdatetime.datetime.strptime(text, fmt).date().togregorian()
                except ValueError:
                    continue
            if self.input_formats:
                raise ValueError(text)
            return to_jalali(text, jalali=True).togregorian()
        except (TypeError, ValueError):
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")

    def prepare_value(self, value):
        if isinstance(value, (dt.date, jdatetime.date)):
            return to_jalali(value).strftime("%Y-%m-%d")
        return value


class JalaliDateTimeField(_ChangeDetectionMixin, forms.Field):
    widget = JalaliDateTimeWidget
    default_error_messages = {
        "invalid": "Enter a valid Jalali datetime in YYYY-MM-DDTHH:MM[:SS] format."
    }

    def to_python(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, (jdatetime.datetime, dt.datetime)):
            return to_jalali_datetime(value).togregorian()
        try:
            return to_jalali_datetime(
                normalize_digits(force_str(value)), jalali=True
            ).togregorian()
        except (TypeError, ValueError):
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")

    def prepare_value(self, value):
        if isinstance(value, (dt.datetime, jdatetime.datetime)):
            return to_jalali_datetime(value).strftime("%Y-%m-%d %H:%M:%S")
        return value


class JalaliTimeField(forms.TimeField):
    widget = JalaliTimeWidget

    def to_python(self, value):
        if isinstance(value, str):
            value = normalize_digits(value)
        return super().to_python(value)


class SplitJalaliDateTimeField(forms.MultiValueField):
    widget = JalaliSplitDateTimeWidget

    def __init__(
        self,
        *,
        require_all_fields=True,
        input_date_formats=None,
        input_time_formats=None,
        **kwargs,
    ):
        fields = (
            JalaliDateField(
                required=require_all_fields, input_formats=input_date_formats
            ),
            JalaliTimeField(
                required=require_all_fields, input_formats=input_time_formats
            ),
        )
        super().__init__(fields=fields, require_all_fields=require_all_fields, **kwargs)

    def compress(self, data_list):
        if not data_list or any(value in (None, "") for value in data_list):
            return None
        date, time = data_list
        # The user typed wall-clock time, i.e. the current time zone.
        return _make_aware(dt.datetime.combine(date, time))


# Names used by django-jalali (django_jalali.forms).
jDateField = JalaliDateField
jDateTimeField = JalaliDateTimeField
