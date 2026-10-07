import warnings
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone

import jdatetime
import pytest
from django.core import serializers
from django.core.exceptions import FieldError, ValidationError
from django.db import connection
from django.db.models import F
from django.test import override_settings
from django.utils import timezone

from jalali_suite.models import JalaliDateField, JalaliDateTimeField
from jalali_suite.utils import to_jalali_datetime
from tests.testapp.models import Event

UTC = dt_timezone.utc
NOWRUZ_1403 = date(2024, 3, 20)
NOON_UTC = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)  # 15:30 in Tehran

pytestmark = pytest.mark.django_db


def raw_value(column, pk):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM testapp_event WHERE id = %s", [pk])
        return cursor.fetchone()[0]


# --- types ------------------------------------------------------------------


def test_attribute_type_is_the_same_before_and_after_a_round_trip():
    event = Event(day=NOWRUZ_1403, at=NOON_UTC)
    assert isinstance(event.day, jdatetime.date)
    assert isinstance(event.at, jdatetime.datetime)

    event.save()
    loaded = Event.objects.get(pk=event.pk)
    assert type(loaded.day) is type(event.day)
    assert type(loaded.at) is type(event.at)


def test_assignment_accepts_many_input_types():
    event = Event()
    for value in (NOWRUZ_1403, "1403-01-01", "2024-03-20", jdatetime.date(1403, 1, 1)):
        event.day = value
        assert event.day == jdatetime.date(1403, 1, 1)
        assert isinstance(event.day, jdatetime.date)

    event.at = "1403-01-01 15:30"
    assert event.at == NOON_UTC
    event.at = NOON_UTC.isoformat()
    assert event.at == NOON_UTC
    event.at = NOWRUZ_1403  # a bare date means midnight
    assert (event.at.hour, event.at.minute) == (0, 0)


def test_none_is_preserved():
    event = Event.objects.create()
    loaded = Event.objects.get(pk=event.pk)
    assert loaded.day is None and loaded.at is None
    assert Event.objects.filter(day__isnull=True).count() == 1


def test_invalid_assignment_is_reported_by_full_clean_not_at_assignment():
    event = Event(day="garbage", at="also garbage")
    with pytest.raises(ValidationError) as caught:
        event.full_clean()
    assert {"day", "at"} <= set(caught.value.message_dict)


# --- storage and time zones -------------------------------------------------


def test_database_stores_gregorian_utc():
    event = Event.objects.create(day=jdatetime.date(1403, 1, 1), at=NOON_UTC)
    assert str(raw_value("day", event.pk)) == "2024-03-20"
    assert str(raw_value("at", event.pk)).startswith("2024-03-20 12:00:00")


def test_values_come_back_in_the_current_time_zone():
    event = Event.objects.create(at=NOON_UTC)
    loaded = Event.objects.get(pk=event.pk)

    assert (loaded.at.hour, loaded.at.minute) == (15, 30)
    assert loaded.at.utcoffset() == timedelta(hours=3, minutes=30)
    assert timezone.is_aware(loaded.at)
    assert loaded.at == NOON_UTC
    # ... which matches what Django itself displays for the same value.
    assert timezone.localtime(NOON_UTC).hour == loaded.at.hour


@pytest.mark.parametrize("zone", ["UTC", "Asia/Tehran", "America/New_York"])
def test_repeated_reload_and_save_never_shifts_the_stored_instant(zone):
    with override_settings(TIME_ZONE=zone):
        event = Event.objects.create(at=NOON_UTC)
        for _ in range(3):
            event = Event.objects.get(pk=event.pk)
            event.save()
        assert Event.objects.get(pk=event.pk).at == NOON_UTC
        assert str(raw_value("at", event.pk)).startswith("2024-03-20 12:00:00")


def test_typed_wall_clock_time_is_saved_as_the_same_local_instant():
    event = Event(at="1403-01-01 15:30:00")
    event.save()
    assert str(raw_value("at", event.pk)).startswith("2024-03-20 12:00:00")


def test_naive_datetimes_warn_like_django_and_use_the_default_time_zone():
    event = Event(at=datetime(2024, 3, 20, 15, 30))
    with pytest.warns(RuntimeWarning, match="naive datetime"):
        event.save()
    assert Event.objects.get(pk=event.pk).at == NOON_UTC


def test_aware_values_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Event.objects.create(at=NOON_UTC)


# --- interoperability with standard types -----------------------------------


def test_values_compare_and_calculate_like_standard_ones():
    event = Event.objects.create(day=NOWRUZ_1403, at=NOON_UTC)
    loaded = Event.objects.get(pk=event.pk)

    assert loaded.day == NOWRUZ_1403
    assert loaded.day < date(2030, 1, 1)
    assert loaded.at == NOON_UTC
    assert loaded.at < timezone.now()
    assert isinstance(timezone.now() - loaded.at, timedelta)
    assert loaded.at + timedelta(days=1) > loaded.at
    assert sorted([loaded.at, NOON_UTC - timedelta(hours=1)])[0] < loaded.at


def test_defaults_and_auto_fields_are_jalali_valued():
    event = Event.objects.create()
    for value in (event.created, event.stamped):
        assert isinstance(value, jdatetime.datetime)
        assert timezone.is_aware(value)
    assert isinstance(event.touched, jdatetime.date)
    assert abs(event.stamped - timezone.now()) < timedelta(seconds=30)


# --- querying ---------------------------------------------------------------


def test_filtering_with_jalali_gregorian_and_string_values():
    first = Event.objects.create(day=NOWRUZ_1403, at=NOON_UTC)
    Event.objects.create(day=date(2025, 1, 1), at=NOON_UTC + timedelta(days=300))

    assert list(Event.objects.filter(day=jdatetime.date(1403, 1, 1))) == [first]
    assert list(Event.objects.filter(day="1403-01-01")) == [first]
    assert list(Event.objects.filter(day=NOWRUZ_1403)) == [first]
    assert Event.objects.filter(day__gte=jdatetime.date(1403, 6, 1)).count() == 1
    assert Event.objects.filter(at__lt=NOON_UTC + timedelta(days=1)).count() == 1
    assert Event.objects.filter(day__in=["1403-01-01", date(2025, 1, 1)]).count() == 2


def test_update_and_values_use_jalali_values():
    event = Event.objects.create(day=NOWRUZ_1403)
    Event.objects.filter(pk=event.pk).update(day=jdatetime.date(1404, 1, 1))
    assert str(raw_value("day", event.pk)) == "2025-03-21"
    assert list(Event.objects.values_list("day", flat=True)) == [
        jdatetime.date(1404, 1, 1)
    ]
    Event.objects.filter(pk=event.pk).update(day=F("day"))  # no crash


def test_year_lookup_on_date_field_follows_the_jalali_calendar():
    days = {
        "last of 1402": date(2024, 3, 19),
        "first of 1403": date(2024, 3, 20),
        "last of 1403": date(2025, 3, 20),  # Esfand 30 in a leap year
        "first of 1404": date(2025, 3, 21),
    }
    for title, day in days.items():
        Event.objects.create(title=title, day=day)

    def titles(**lookup):
        return {e.title for e in Event.objects.filter(**lookup)}

    assert titles(day__year=1403) == {"first of 1403", "last of 1403"}
    assert titles(day__year__gte=1403) == {
        "first of 1403",
        "last of 1403",
        "first of 1404",
    }
    assert titles(day__year__gt=1403) == {"first of 1404"}
    assert titles(day__year__lt=1403) == {"last of 1402"}
    assert titles(day__year__lte=1402) == {"last of 1402"}


def test_year_lookup_on_datetime_field_respects_the_local_time_zone():
    # Just either side of Nowruz midnight in Tehran. In UTC both of the
    # "outer" values fall on the *other* calendar day than they do locally.
    moments = {
        "1402 end": to_jalali_datetime("1402-12-29 23:50"),
        "1403 start": to_jalali_datetime("1403-01-01 00:10"),
        "1403 end": to_jalali_datetime("1403-12-30 23:50"),
        "1404 start": to_jalali_datetime("1404-01-01 00:10"),
    }
    for title, moment in moments.items():
        Event.objects.create(title=title, at=moment)

    got = {e.title for e in Event.objects.filter(at__year=1403)}
    assert got == {"1403 start", "1403 end"}
    assert Event.objects.filter(at__year__lt=1403).get().title == "1402 end"


def test_month_day_and_quarter_lookups_refuse_to_silently_use_gregorian():
    for lookup in ("day__month", "day__day", "at__month", "at__quarter"):
        with pytest.raises(FieldError, match="not supported"):
            Event.objects.filter(**{lookup: 1})


def test_year_cannot_be_used_as_a_sql_expression():
    with pytest.raises(FieldError, match="integer"):
        list(Event.objects.annotate(y=F("day__year")))


def test_other_lookups_still_work():
    Event.objects.create(day=NOWRUZ_1403, at=NOON_UTC)
    assert Event.objects.filter(at__hour=15).count() == 1  # local hour
    assert Event.objects.filter(at__date=NOWRUZ_1403).count() == 1
    assert Event.objects.filter(day__range=(date(2024, 1, 1), date(2025, 1, 1))).count() == 1


# --- serialization ----------------------------------------------------------


def test_serialization_uses_gregorian_values_and_round_trips():
    event = Event.objects.create(day=NOWRUZ_1403, at=NOON_UTC)
    payload = serializers.serialize("json", [event], fields=("day", "at"))

    assert "2024-03-20" in payload
    assert "1403" not in payload

    restored = next(serializers.deserialize("json", payload)).object
    assert restored.day == jdatetime.date(1403, 1, 1)
    assert restored.at == NOON_UTC


# --- field definition -------------------------------------------------------


def test_fields_deconstruct_to_their_public_path():
    assert Event._meta.get_field("day").deconstruct()[1] == (
        "jalali_suite.models.JalaliDateField"
    )
    assert Event._meta.get_field("at").deconstruct()[1] == (
        "jalali_suite.models.JalaliDateTimeField"
    )
    assert issubclass(JalaliDateField, type(Event._meta.get_field("day")))
    assert issubclass(JalaliDateTimeField, type(Event._meta.get_field("at")))
