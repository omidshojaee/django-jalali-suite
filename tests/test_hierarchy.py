import html as htmllib
import re
from datetime import date

import jdatetime
import pytest
from django.urls import reverse
from django.utils import translation

from jalali_suite import to_jalali_datetime
from jalali_suite.apps import check_date_hierarchy
from jalali_suite.query import jalali_dates
from tests.testapp.models import Event, Plain

pytestmark = pytest.mark.django_db


@pytest.fixture
def events():
    """Moments either side of Jalali year, month and day boundaries (Tehran time)."""
    for title, text in {
        "e1": "1402-12-29 23:50",  # last minute of 1402
        "e2": "1403-01-01 00:10",  # first minutes of 1403
        "e3": "1403-02-15 12:00",
        "e4": "1404-06-01 09:00",
    }.items():
        Event.objects.create(title=title, at=to_jalali_datetime(text))


def fetch(client, name, **params):
    response = client.get(reverse(f"hier:testapp_{name}_changelist"), params)
    return response


def titles(response):
    return sorted(e.title for e in response.context["cl"].result_list)


def hierarchy_links(response):
    """(text, href) of every link inside the date-hierarchy nav."""
    page = response.content.decode()
    nav = re.search(r'<nav class="toplinks".*?</nav>', page, re.S)
    assert nav, "no date hierarchy rendered"
    return [
        # Django's template prefixes the "back" link with a single-angle quote.
        (re.sub(r"\s+", " ", htmllib.unescape(text).replace("‹", "")).strip(), htmllib.unescape(href))
        for href, text in re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>', nav.group(0), re.S)
    ]


def test_top_level_lists_jalali_years(admin_client, events):
    response = fetch(admin_client, "event")
    assert response.status_code == 200
    assert titles(response) == ["e1", "e2", "e3", "e4"]
    assert hierarchy_links(response) == [
        ("1402", "?at__year=1402"),
        ("1403", "?at__year=1403"),
        ("1404", "?at__year=1404"),
    ]


def test_year_level_filters_by_jalali_year_and_lists_months(admin_client, events):
    response = fetch(admin_client, "event", at__year=1403)
    assert titles(response) == ["e2", "e3"]
    links = hierarchy_links(response)
    assert links[0][0].endswith("All dates")
    assert ("فروردین 1403", "?at__month=1&at__year=1403") in links or (
        "فروردین 1403",
        "?at__year=1403&at__month=1",
    ) in links
    assert any(text == "اردیبهشت 1403" for text, _ in links)
    assert not any(text.endswith("1404") for text, _ in links)


def test_year_boundaries_follow_local_midnight(admin_client, events):
    # e1 is 23:50 on the last day of 1402 in Tehran, which is the previous
    # *Gregorian day* in UTC; e2 is 00:10 on Nowruz, i.e. also 19 March in UTC.
    assert titles(fetch(admin_client, "event", at__year=1402)) == ["e1"]
    assert titles(fetch(admin_client, "event", at__year=1403, at__month=1)) == ["e2"]


def test_month_level_lists_days(admin_client, events):
    response = fetch(admin_client, "event", at__year=1403, at__month=1)
    links = hierarchy_links(response)
    assert links[0][0] == "1403"
    assert [text for text, _ in links[1:]] == ["01 فروردین"]
    assert "at__day=1" in links[1][1]


def test_day_level_filters_one_day_and_links_back(admin_client, events):
    response = fetch(admin_client, "event", at__year=1403, at__month=1, at__day=1)
    assert titles(response) == ["e2"]
    assert hierarchy_links(response)[0][0] == "فروردین 1403"


def test_invalid_jalali_numbers_are_rejected_not_misread(admin_client, events):
    for params in ({"at__year": 1403, "at__month": 13}, {"at__year": 1403, "at__month": 7, "at__day": 31}):
        response = fetch(admin_client, "event", **params)
        assert response.status_code == 302 and response["Location"].endswith("?e=1")


def test_a_single_month_opens_straight_at_the_day_level(admin_client):
    Event.objects.create(at=to_jalali_datetime("1403-03-05 10:00"))
    Event.objects.create(at=to_jalali_datetime("1403-03-20 10:00"))

    links = hierarchy_links(fetch(admin_client, "event"))
    assert [text for text, _ in links] == ["1403", "05 خرداد", "20 خرداد"]


def test_digits_follow_the_site_language(admin_client, events):
    with translation.override("fa"):
        response = fetch(admin_client, "event")
    assert [text for text, _ in hierarchy_links(response)] == ["۱۴۰۲", "۱۴۰۳", "۱۴۰۴"]


def test_plain_django_date_fields_drill_down_by_the_jalali_calendar(admin_client):
    for day in (date(2024, 3, 19), date(2024, 3, 20), date(2025, 3, 21)):
        Plain.objects.create(title=day.isoformat(), day=day)

    # Gregorian 2024 would match two rows; Jalali 1403 matches exactly one.
    response = fetch(admin_client, "plain", day__year=1403)
    assert titles(response) == ["2024-03-20"]
    assert [text for text, _ in hierarchy_links(fetch(admin_client, "plain"))] == [
        "1402",
        "1403",
        "1404",
    ]


# --- system check -----------------------------------------------------------


def test_check_is_registered_with_djangos_check_framework():
    from django.core import checks

    found = [
        message
        for message in checks.run_checks(tags=[checks.Tags.admin])
        if message.id == "jalali_suite.W001"
    ]
    assert len(found) == 1


def test_check_warns_only_for_admins_that_would_use_the_gregorian_calendar():
    warnings = check_date_hierarchy()

    assert [w.id for w in warnings] == ["jalali_suite.W001"]
    assert warnings[0].obj.__name__ == "BareEventAdmin"
    assert "Gregorian" in warnings[0].msg


# --- jalali_dates() ---------------------------------------------------------


def test_jalali_dates_truncates_on_the_jalali_calendar(events):
    qs = Event.objects.all()
    assert jalali_dates(qs, "at", "year") == [
        jdatetime.date(1402, 1, 1),
        jdatetime.date(1403, 1, 1),
        jdatetime.date(1404, 1, 1),
    ]
    assert jalali_dates(qs, "at", "month") == [
        jdatetime.date(1402, 12, 1),
        jdatetime.date(1403, 1, 1),
        jdatetime.date(1403, 2, 1),
        jdatetime.date(1404, 6, 1),
    ]
    assert jalali_dates(qs, "at")[:2] == [jdatetime.date(1402, 12, 29), jdatetime.date(1403, 1, 1)]


def test_jalali_dates_works_on_plain_fields_and_ignores_nulls():
    Plain.objects.create(day=date(2024, 3, 20))
    Plain.objects.create(day=date(2024, 3, 20))
    Plain.objects.create(day=None)
    assert jalali_dates(Plain.objects.all(), "day", "year") == [jdatetime.date(1403, 1, 1)]


def test_jalali_dates_rejects_unknown_kinds():
    with pytest.raises(ValueError, match="kind"):
        jalali_dates(Event.objects.all(), "at", "week")
