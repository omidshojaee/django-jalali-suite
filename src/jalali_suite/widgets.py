from django import forms
from django.contrib.admin.widgets import AdminDateWidget, AdminTimeWidget
from django.forms.utils import to_current_timezone

from .utils import JalaliDate, JalaliDateTime, to_jalali, to_jalali_datetime


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
    date_widget_class = JalaliDateWidget
    time_widget_class = forms.TimeInput

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
    time_widget_class = AdminTimeWidget
