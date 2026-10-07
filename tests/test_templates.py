from datetime import date, datetime
from datetime import timezone as dt_timezone

import jdatetime
import pytest
from django.template import Context, Template
from django.utils import translation

UTC = dt_timezone.utc


def render(source, **context):
    return Template("{% load jalali_suite %}" + source).render(Context(context))


def test_filter_and_tag_use_site_language_for_digits():
    with translation.override("fa"):
        rendered = render("{{ value|jalali }} {% jalali_date value %}", value=date(2024, 3, 20))
    assert rendered == "۱۴۰۳/۰۱/۰۱ ۱۴۰۳/۰۱/۰۱"


@pytest.mark.parametrize("name", ["jalali", "jformat", "to_jalali"])
def test_filter_names_from_the_other_packages_work(name):
    value = date(2024, 3, 20)
    assert render("{{ value|%s:'%%Y/%%m/%%d' }}" % name, value=value) == "1403/01/01"
    assert render("{{ value|%s }}" % name, value=value) == "1403/01/01"


def test_tag_accepts_already_jalali_values_and_aware_datetimes():
    assert render("{% jalali_date value %}", value=jdatetime.date(1403, 1, 1)) == "1403/01/01"
    assert (
        render("{% jalali_date value %}", value=jdatetime.datetime(1403, 1, 1, 12, 30))
        == "1403/01/01 12:30:00"
    )
    # Aware values are shown in the current time zone (Tehran in the tests).
    aware = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)
    assert render("{{ value|jalali }}", value=aware) == "1403/01/01 15:30:00"


def test_empty_and_unsupported_values_render_a_dash():
    assert render("{{ value|jalali }}", value=None) == "-"
    assert render("{{ value|jalali_digits }}", value="") == "-"
    assert render("{% jalali_date value %}", value="not a date") == "-"


def test_digits_filter_overrides_site_language():
    value = date(2024, 3, 20)
    with translation.override("fa"):
        assert render("{{ value|jalali_digits:'latin' }}", value=value) == "1403/01/01"
    with translation.override("en"):
        assert render("{{ value|jalali_digits:'farsi' }}", value=value) == "۱۴۰۳/۰۱/۰۱"


def test_jalali_now_uses_the_current_time_zone():
    rendered = render("{% jalali_now '%Y' %}")
    assert rendered.isdigit() and 1400 <= int(rendered) < 1700
