from django import forms
from django.contrib.admin.widgets import AdminDateWidget, AdminTimeWidget
from django.forms.utils import to_current_timezone

from .utils import (
    JalaliDate,
    JalaliDateTime,
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
            isoformat = to_jalali(value).isoformat
        except (TypeError, ValueError):
            # Django re-renders a bound-but-invalid form with the raw
            # submitted string so the user can see and fix their typo;
            # echo it back unchanged rather than crashing on it.
            return value
        return to_farsi_digits(isoformat) if uses_farsi_digits() else isoformat


class AdminJalaliDateWidget(JalaliDateWidget, AdminDateWidget):
    pass


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
        if isinstance(value, JalaliDateTime):
            return [
                f"{value.year:04d}-{value.month:02d}-{value.day:02d}",
                value.to_datetime().time().replace(microsecond=0),
            ]
        value = to_current_timezone(value)
        jvalue = to_jalali_datetime(value)
        return [
            f"{jvalue.year:04d}-{jvalue.month:02d}-{jvalue.day:02d}",
            value.time().replace(microsecond=0),
        ]


class AdminJalaliSplitDateTimeWidget(JalaliSplitDateTimeWidget):
    date_widget_class = AdminJalaliDateWidget
    time_widget_class = AdminJalaliTimeWidget
