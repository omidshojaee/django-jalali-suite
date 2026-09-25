from datetime import date, datetime

from django.template import Context, Template
from django.utils import translation

from jalali_suite import JalaliDate, JalaliDateTime, format_jalali, to_jalali_datetime
from jalali_suite.admin import JalaliDateModelAdmin


def test_datetime_round_trip_and_formatting():
    value = to_jalali_datetime(datetime(2024, 3, 20, 12, 30, 45))
    assert value == JalaliDateTime(1403, 1, 1, 12, 30, 45)
    assert value.to_datetime() == datetime(2024, 3, 20, 12, 30, 45)
    assert (
        format_jalali(datetime(2024, 3, 20, 12, 30, 45), "%Y/%m/%d %H:%M")
        == "1403/01/01 12:30"
    )


def test_format_jalali_supports_month_and_12hour_directives():
    value = datetime(2026, 8, 27, 14, 11, 0)
    assert (
        format_jalali(value, "%y/%b/%d %I:%M %p")
        == "05/شهر/05 02:11 بعد از ظهر"
    )
    assert format_jalali(value, "%A %B") == "پنج‌شنبه شهریور"


def test_template_filter_and_tag_use_site_language_for_digits():
    with translation.override("fa"):
        rendered = Template(
            "{% load jalali_suite %}{{ value|jalali }} {% jalali_date value %}"
        ).render(Context({"value": date(2024, 3, 20)}))
    assert rendered == "۱۴۰۳/۰۱/۰۱ ۱۴۰۳/۰۱/۰۱"


def test_jalali_date_tag_accepts_already_jalali_values():
    # JalaliDateField/JalaliDateTimeField model fields hand out JalaliDate/
    # JalaliDateTime instances (not datetime.date/datetime), which is the
    # most common input this tag sees in practice.
    rendered = Template(
        "{% load jalali_suite %}{% jalali_date value %}"
    ).render(Context({"value": JalaliDate(1403, 1, 1)}))
    assert rendered == "1403/01/01"

    rendered = Template(
        "{% load jalali_suite %}{% jalali_date value %}"
    ).render(Context({"value": JalaliDateTime(1403, 1, 1, 12, 30)}))
    assert rendered == "1403/01/01 12:30:00"


def test_jalali_digits_filter_overrides_site_language():
    value = date(2024, 3, 20)
    with translation.override("fa"):
        assert format_jalali(value, digits="latin") == "1403/01/01"
    with translation.override("en"):
        assert format_jalali(value, digits="farsi") == "۱۴۰۳/۰۱/۰۱"


def test_split_datetime_widget_time_subwidget_follows_site_language():
    from jalali_suite.forms import SplitJalaliDateTimeField
    from jalali_suite.widgets import JalaliSplitDateTimeWidget

    value = datetime(2026, 8, 27, 14, 11, 0)

    with translation.override("fa"):
        rendered = JalaliSplitDateTimeWidget().render("created_at", value)
    assert 'value="۱۴:۱۱:۰۰"' in rendered

    with translation.override("en"):
        rendered = JalaliSplitDateTimeWidget().render("created_at", value)
    assert 'value="14:11:00"' in rendered

    with translation.override("fa"):
        cleaned = SplitJalaliDateTimeField().clean(["1405-06-05", "۱۴:۱۱:۰۰"])
    assert cleaned == JalaliDateTime(1405, 6, 5, 14, 11, 0)


def test_admin_media_includes_bundled_font():
    from django.contrib import admin
    from test_django_integration import DemoModel

    instance = JalaliDateModelAdmin(DemoModel, admin.site)
    assert "jalali_suite/css/vazirmatn.css" in instance.media._css["all"]
