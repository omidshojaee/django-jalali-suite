import datetime as dt

from django import forms
from django.utils.encoding import force_str

from .utils import (
    JalaliDate,
    JalaliDateTime,
    normalize_digits,
    to_gregorian,
    to_jalali,
    to_jalali_datetime,
)
from .widgets import JalaliDateWidget, JalaliSplitDateTimeWidget


class JalaliDateField(forms.Field):
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
        if isinstance(value, JalaliDate):
            return value
        try:
            cleaned = normalize_digits(force_str(value).strip()).replace("/", "-")
            year, month, day = map(int, cleaned.split("-"))
            return JalaliDate(year, month, day)
        except (TypeError, ValueError):
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")

    def prepare_value(self, value):
        if isinstance(value, JalaliDate):
            return value.isoformat
        if isinstance(value, (dt.date, dt.datetime)):
            return to_jalali(value).isoformat
        return value


class JalaliDateTimeField(forms.Field):
    default_error_messages = {
        "invalid": "Enter a valid Jalali datetime in YYYY-MM-DDTHH:MM[:SS] format."
    }

    def to_python(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, JalaliDateTime):
            return value
        try:
            return to_jalali_datetime(normalize_digits(force_str(value)))
        except (TypeError, ValueError):
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")


class SplitJalaliDateTimeField(forms.MultiValueField):
    widget = JalaliSplitDateTimeWidget

    def __init__(self, *, require_all_fields=True, **kwargs):
        fields = (
            JalaliDateField(required=require_all_fields),
            forms.TimeField(required=require_all_fields),
        )
        super().__init__(fields=fields, require_all_fields=require_all_fields, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return None
        if any(value in (None, "") for value in data_list):
            return None
        jdate, time = data_list
        return JalaliDateTime(
            jdate.year,
            jdate.month,
            jdate.day,
            time.hour,
            time.minute,
            time.second,
            time.microsecond,
        )
