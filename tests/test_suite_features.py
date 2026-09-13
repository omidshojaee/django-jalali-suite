from datetime import date, datetime

from django.template import Context, Template
from django.test import override_settings

from jalali_suite import JalaliDateTime, format_jalali, to_jalali_datetime
from jalali_suite.admin import JalaliDateModelAdmin


def test_datetime_round_trip_and_formatting():
    value = to_jalali_datetime(datetime(2024, 3, 20, 12, 30, 45))
    assert value == JalaliDateTime(1403, 1, 1, 12, 30, 45)
    assert value.to_datetime() == datetime(2024, 3, 20, 12, 30, 45)
    assert (
        format_jalali(datetime(2024, 3, 20, 12, 30, 45), "%Y/%m/%d %H:%M")
        == "1403/01/01 12:30"
    )


def test_template_filter_and_tag_use_project_digit_setting():
    with override_settings(JALALI_SUITE={"DIGITS": "farsi"}):
        rendered = Template(
            "{% load jalali_suite %}{{ value|jalali }} {% jalali_date value %}"
        ).render(Context({"value": date(2024, 3, 20)}))
    assert rendered == "۱۴۰۳/۰۱/۰۱ ۱۴۰۳/۰۱/۰۱"


def test_admin_media_includes_bundled_font():
    from django.contrib import admin
    from test_django_integration import DemoModel

    instance = JalaliDateModelAdmin(DemoModel, admin.site)
    assert "jalali_suite/css/vazirmatn.css" in instance.media._css["all"]
