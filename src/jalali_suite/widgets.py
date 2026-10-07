import datetime as dt

import jdatetime
from django import forms
from django.contrib.admin.widgets import AdminDateWidget, AdminTimeWidget

from .utils import (
    to_farsi_digits,
    to_jalali,
    to_jalali_datetime,
    uses_farsi_digits,
)


class JalaliDateWidget(forms.DateInput):
    input_type = "text"
    template_name = "jalali_suite/widgets/jalali_date.html"

    class Media:
        css = {
            "all": (
                "jalali_suite/css/vazirmatn.css",
                "jalali_suite/css/jalali-datepicker.css",
            )
        }
        js = ("jalali_suite/js/jalali-datepicker.js",)

    def __init__(self, attrs=None, format=None):
        final_attrs = {"class": "jalali-suite-date", "data-jalali-datepicker": "true"}
        final_attrs.update(attrs or {})
        super().__init__(attrs=final_attrs, format=format)

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs["data-digits"] = "farsi" if uses_farsi_digits() else "latin"
        return attrs

    def format_value(self, value):
        if value in (None, ""):
            return None
        try:
            # A string here is what the user typed, so it is Jalali; only real
            # date objects need converting.
            if isinstance(value, str):
                text = to_jalali(value, jalali=True).strftime("%Y-%m-%d")
            else:
                text = to_jalali(value).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            # Django re-renders a bound-but-invalid form with the raw
            # submitted string so the user can see and fix their typo;
            # echo it back unchanged rather than crashing on it.
            return value
        return to_farsi_digits(text) if uses_farsi_digits() else text


class AdminJalaliDateWidget(JalaliDateWidget, AdminDateWidget):
    pass


class JalaliDateTimeWidget(forms.DateTimeInput):
    """Single text input for a Jalali date and time, e.g. ``1403-01-01 15:30:00``."""

    input_type = "text"

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs["data-digits"] = "farsi" if uses_farsi_digits() else "latin"
        return attrs

    def format_value(self, value):
        if value in (None, ""):
            return None
        try:
            jvalue = to_jalali_datetime(
                value, jalali=True if isinstance(value, str) else None
            )
        except (TypeError, ValueError):
            return value  # re-rendering a rejected submission: echo it back
        text = jvalue.strftime("%Y-%m-%d %H:%M:%S")
        return to_farsi_digits(text) if uses_farsi_digits() else text


class JalaliTimeWidget(forms.TimeInput):
    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs["data-digits"] = "farsi" if uses_farsi_digits() else "latin"
        return attrs

    def format_value(self, value):
        formatted = super().format_value(value)
        if formatted in (None, ""):
            return formatted
        return to_farsi_digits(formatted) if uses_farsi_digits() else formatted


class AdminJalaliTimeWidget(JalaliTimeWidget, AdminTimeWidget):
    pass


class JalaliSplitDateTimeWidget(forms.MultiWidget):
    template_name = "jalali_suite/widgets/jalali_split_datetime.html"
    date_widget_class = JalaliDateWidget
    time_widget_class = JalaliTimeWidget

    def __init__(self, attrs=None):
        super().__init__((self.date_widget_class, self.time_widget_class), attrs)

    def decompress(self, value):
        if not value:
            return [None, None]
        if isinstance(value, (dt.datetime, jdatetime.datetime)):
            # Show wall-clock time in the current time zone.
            jvalue = to_jalali_datetime(value)
            return [
                jvalue.strftime("%Y-%m-%d"),
                jvalue.time().replace(microsecond=0),
            ]
        return [None, None]


class AdminJalaliSplitDateTimeWidget(JalaliSplitDateTimeWidget):
    date_widget_class = AdminJalaliDateWidget
    time_widget_class = AdminJalaliTimeWidget


# Names used by django-jalali-date and django-jalali.
AdminSplitJalaliDateTime = AdminJalaliSplitDateTimeWidget
jDateInput = JalaliDateWidget
jDateTimeInput = JalaliDateTimeWidget
