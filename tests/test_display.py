"""What a Persian-speaking user sees for a Jalali field, and what must not change.

With the language set to ``fa``, the admin and the package's tags and filters show
Jalali dates with Persian month names and Persian digits. The *value* itself never
depends on the language: ``str()`` is the same in every language, and Django's own
filters and settings are left exactly as they are.
"""

from datetime import date, datetime
from datetime import timezone as dt_timezone

import jdatetime
import pytest
from django.contrib import admin
from django.template import Context, Template
from django.urls import reverse
from django.utils import translation

from jalali_suite import JalaliDate, JalaliDateTime
from tests.testapp.models import Event, Plain

UTC = dt_timezone.utc
NOON_UTC = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)  # 15:30 in Tehran, a Wednesday

MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]  # fmt: skip
GREGORIAN_MONTH_NAMES = ("ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن", "ژوئیه", "اوت")


@pytest.fixture
def event(db):
    created = Event.objects.create(day=date(2024, 3, 20), at=NOON_UTC)
    return Event.objects.get(pk=created.pk)  # as loaded from the database


def render(source, **context):
    return Template("{% load jalali_suite %}" + source).render(Context(context))


# --- the value never depends on the language --------------------------------


def test_field_values_are_the_suite_types_however_they_arrive(event):
    assert type(event.day) is JalaliDate
    assert type(event.at) is JalaliDateTime
    fresh = Event(day=date(2024, 3, 20), at=NOON_UTC)
    assert type(fresh.day) is JalaliDate and type(fresh.at) is JalaliDateTime
    fresh.day = "1403-01-01"
    assert type(fresh.day) is JalaliDate


@pytest.mark.parametrize("language", ["fa", "en", "de"])
def test_str_is_iso_in_every_language(event, language):
    with translation.override(language):
        assert str(event.day) == "1403-01-01"
        assert str(event.at).startswith("1403-01-01 15:30:00")
        assert f"{event.day}" == "1403-01-01"
        assert event.day.isoformat() == "1403-01-01"


def test_f_string_of_a_jalali_value_is_not_empty():
    # jdatetime formats an empty spec as "", which made f"{value}" vanish.
    assert f"{JalaliDate(1403, 1, 1)}" == "1403-01-01"
    assert format(JalaliDate(1403, 1, 1), "") == "1403-01-01"
    assert f"{JalaliDate(1403, 1, 1):%Y/%m/%d}" == "1403/01/01"


def test_values_still_behave_like_dates(event):
    assert event.day == date(2024, 3, 20)
    assert event.day < date(2030, 1, 1)
    assert event.at == NOON_UTC
    assert hash(event.day) == hash(jdatetime.date(1403, 1, 1))


def test_bare_template_output_is_the_plain_iso_value_in_every_language(event):
    for language in ("fa", "en"):
        with translation.override(language):
            assert render("{{ e.day }}", e=event) == "1403-01-01"


# --- the explicit tags and filters, under fa --------------------------------


def test_jalali_filter_uses_persian_month_names_and_digits_under_fa(event):
    with translation.override("fa"):
        assert render("{{ e.day|jalali:'%d %B %Y' }}", e=event) == "۰۱ فروردین ۱۴۰۳"
        assert render("{{ e.day|jalali:'%A' }}", e=event) == "چهارشنبه"
        assert render("{{ e.at|jalali:'%H:%M' }}", e=event) == "۱۵:۳۰"
        assert render("{% jalali_date e.day '%d %B %Y' %}", e=event) == "۰۱ فروردین ۱۴۰۳"
    with translation.override("en"):  # month names stay Persian; only digits change
        assert render("{{ e.day|jalali:'%d %B %Y' }}", e=event) == "01 فروردین 1403"


def test_every_month_has_its_persian_name_and_never_a_gregorian_one():
    for month, name in enumerate(MONTHS, start=1):
        value = JalaliDate(1403, month, 1)
        for language in ("fa", "en"):
            with translation.override(language):
                rendered = render("{{ v|jalali:'%B' }}", v=value)
            assert rendered == name
            assert rendered not in GREGORIAN_MONTH_NAMES


def test_digits_filter_overrides_the_language(event):
    with translation.override("fa"):
        assert render("{{ e.day|jalali_digits:'latin' }}", e=event) == "1403/01/01"
    with translation.override("en"):
        assert render("{{ e.day|jalali_digits:'farsi' }}", e=event) == "۱۴۰۳/۰۱/۰۱"


# --- Django's own filters are not touched -----------------------------------


def test_djangos_date_and_time_filters_are_left_exactly_as_django_has_them():
    from django.template import Engine
    from django.template.defaultfilters import date as django_date

    # The package adds nothing to the template builtins and replaces no filter.
    assert not any("jalali" in name for name in Engine.default_builtins)
    assert not any("jalali" in name for name in Engine.get_default().builtins)

    gregorian = date(2024, 3, 20)
    with translation.override("fa"):
        assert render("{{ v|date:'j F Y' }}", v=gregorian) == django_date(gregorian, "j F Y")


# --- the admin, under fa ----------------------------------------------------


@pytest.mark.django_db
def test_admin_shows_jalali_fields_with_persian_digits_under_fa(admin_client, event):
    with translation.override("fa"):
        listing = admin_client.get(reverse("admin:testapp_event_changelist")).content.decode()
        change = admin_client.get(
            reverse("admin:testapp_event_change", args=[event.pk])
        ).content.decode()

    assert "<bdi>۱۴۰۳/۰۱/۰۱</bdi>" in listing
    assert "<bdi>۱۴۰۳/۰۱/۰۱ ۱۵:۳۰:۰۰</bdi>" in listing
    assert 'value="۱۴۰۳-۰۱-۰۱"' in change
    assert 'value="۱۵:۳۰:۰۰"' in change
    assert "2024" not in listing.split('<table id="result_list"')[1].split("</table>")[0]


# --- plain Django date fields are the developer's business -----------------


@pytest.mark.django_db
def test_admin_leaves_plain_django_date_fields_alone_by_default():
    from jalali_suite.admin import JalaliDateModelAdmin
    from jalali_suite.forms import JalaliDateField

    class PlainDefault(JalaliDateModelAdmin):
        list_display = ("title", "day", "at")
        readonly_fields = ("day",)

    ma = PlainDefault(Plain, admin.site)
    formfield = ma.formfield_for_dbfield(Plain._meta.get_field("day"), request=None)

    assert not isinstance(formfield, JalaliDateField)  # Django's own field and widget
    assert ma.get_list_display(request=None) == ["title", "day", "at"]  # not replaced
    assert list(ma.get_readonly_fields(request=None)) == ["day"]
    obj = Plain(day=date(2024, 3, 20))
    assert type(obj.day) is date  # the model value is untouched, too
