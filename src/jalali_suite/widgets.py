from django import forms
from django.contrib.admin.widgets import AdminDateWidget, AdminTimeWidget
from django.forms.utils import to_current_timezone

from .utils import JalaliDate, to_jalali, to_jalali_datetime


class JalaliDateWidget(forms.DateInput):
    input_type = "text"
    template_name = "jalali_suite/widgets/jalali_date.html"

    def __init__(self, attrs=None, format=None):
        final_attrs = {"class": "jalali-suite-date", "data-jalali-datepicker": "true"}
        final_attrs.update(attrs or {})
        super().__init__(attrs=final_attrs, format=format)

    def format_value(self, value):
        if value in (None, ""):
            return None
        return to_jalali(value).isoformat


class AdminJalaliDateWidget(JalaliDateWidget, AdminDateWidget):
    pass


class JalaliSplitDateTimeWidget(forms.MultiWidget):
    template_name = "jalali_suite/widgets/jalali_split_datetime.html"

    def __init__(self, attrs=None):
        super().__init__((JalaliDateWidget, AdminTimeWidget), attrs)

    def decompress(self, value):
        if not value:
            return [None, None]
        value = to_current_timezone(value)
        jvalue = to_jalali_datetime(value)
        return [
            f"{jvalue.year:04d}-{jvalue.month:02d}-{jvalue.day:02d}",
            value.time().replace(microsecond=0),
        ]


class AdminJalaliSplitDateTimeWidget(JalaliSplitDateTimeWidget):
    pass
