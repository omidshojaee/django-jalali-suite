import datetime as dt

from django.db import models

from .forms import JalaliDateField as JalaliDateFormField
from .forms import SplitJalaliDateTimeField
from .utils import JalaliDate, JalaliDateTime, to_jalali, to_jalali_datetime


class JalaliDateField(models.DateField):
    description = "Jalali date"

    def from_db_value(self, value, expression, connection):
        return None if value is None else to_jalali(value)

    def to_python(self, value):
        if value is None or isinstance(value, JalaliDate):
            return value
        return to_jalali(value)

    def get_prep_value(self, value):
        if isinstance(value, JalaliDate):
            return value.to_gregorian()
        return value

    def formfield(self, **kwargs):
        return super().formfield(form_class=JalaliDateFormField, **kwargs)


class JalaliDateTimeField(models.DateTimeField):
    description = "Jalali datetime"

    def from_db_value(self, value, expression, connection):
        return None if value is None else to_jalali_datetime(value)

    def to_python(self, value):
        if value is None or isinstance(value, JalaliDateTime):
            return value
        return (
            to_jalali_datetime(value)
            if isinstance(value, (dt.datetime, str))
            else value
        )

    def get_prep_value(self, value):
        if isinstance(value, JalaliDateTime):
            return value.to_datetime()
        return value

    def formfield(self, **kwargs):
        return super().formfield(form_class=SplitJalaliDateTimeField, **kwargs)
