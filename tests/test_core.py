from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone

import jdatetime
import pytest

from jalali_suite import (
    JalaliDate,
    JalaliDateTime,
    date2jalali,
    datetime2jalali,
    format_jalali,
    isoformat_jalali,
    jalali_datetime_range,
    jalali_range,
    to_farsi_digits,
    to_gregorian,
    to_jalali,
    to_jalali_datetime,
)

UTC = dt_timezone.utc
TEHRAN_OFFSET = timedelta(hours=3, minutes=30)  # tests run with TIME_ZONE=Asia/Tehran


def test_public_types_are_jdatetime_subclasses():
    assert issubclass(JalaliDate, jdatetime.date)
    assert issubclass(JalaliDateTime, jdatetime.datetime)


def test_jalali_date_aliases_return_none_for_none():
    assert date2jalali(None) is None
    assert datetime2jalali(None) is None
    assert date2jalali(date(2024, 3, 20)) == jdatetime.date(1403, 1, 1)
    assert datetime2jalali(datetime(2024, 3, 20, 12, 0, tzinfo=UTC)) == datetime(
        2024, 3, 20, 12, 0, tzinfo=UTC
    )


# --- dates ------------------------------------------------------------------


def test_known_jalali_conversion():
    value = to_jalali(date(2024, 3, 20))
    assert isinstance(value, jdatetime.date)
    assert value == jdatetime.date(1403, 1, 1)


def test_round_trip_conversion():
    value = jdatetime.date(1403, 1, 1)
    assert value.togregorian() == date(2024, 3, 20)
    assert to_jalali(value) == value
    assert isinstance(to_jalali(value), JalaliDate)
    assert isoformat_jalali(value) == "1403-01-01"


def test_to_gregorian_works_on_components():
    assert to_gregorian(1403, 1, 1) == date(2024, 3, 20)


@pytest.mark.parametrize(
    "text",
    ["1403-01-01", "1403/01/01", "1403-1-1", "۱۴۰۳-۰۱-۰۱", "١٤٠٣/٠١/٠١", " 1403-01-01 "],
)
def test_to_jalali_accepts_jalali_strings(text):
    assert to_jalali(text) == jdatetime.date(1403, 1, 1)


def test_to_jalali_reads_gregorian_strings_by_year():
    assert to_jalali("2024-03-20") == jdatetime.date(1403, 1, 1)
    assert to_jalali("2024-03-20T12:00:00") == jdatetime.date(1403, 1, 1)


def test_to_jalali_can_force_jalali_reading():
    # What a Jalali form input means, even for a year that looks Gregorian.
    assert to_jalali("2024-03-20", jalali=True) == jdatetime.date(2024, 3, 20)


def test_to_jalali_uses_local_date_for_aware_datetimes():
    # 21:00 UTC on 19 March is 00:30 on 20 March in Tehran.
    value = datetime(2024, 3, 19, 21, 0, tzinfo=UTC)
    assert to_jalali(value) == jdatetime.date(1403, 1, 1)


@pytest.mark.parametrize("bad", ["", "nonsense", "1403-13-01", "1403-07-31"])
def test_to_jalali_rejects_bad_strings(bad):
    with pytest.raises(ValueError):
        to_jalali(bad)


def test_to_jalali_rejects_none_and_unknown_types():
    with pytest.raises(ValueError):
        to_jalali(None)
    with pytest.raises(TypeError):
        to_jalali(12345)


# --- datetimes --------------------------------------------------------------


def test_aware_datetime_converts_to_local_time_and_stays_equal():
    original = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)
    value = to_jalali_datetime(original)

    assert isinstance(value, jdatetime.datetime)
    assert (value.year, value.month, value.day) == (1403, 1, 1)
    assert (value.hour, value.minute) == (15, 30)
    assert value.utcoffset() == TEHRAN_OFFSET
    assert value == original  # same instant


def test_naive_datetime_stays_naive():
    value = to_jalali_datetime(datetime(2024, 3, 20, 12, 30, 45))
    assert value.tzinfo is None
    assert (value.hour, value.minute, value.second) == (12, 30, 45)
    assert value == datetime(2024, 3, 20, 12, 30, 45)


def test_jalali_string_without_offset_means_local_wall_clock():
    value = to_jalali_datetime("1403-01-01 15:30")
    assert value == datetime(2024, 3, 20, 12, 0, tzinfo=UTC)
    assert (value.hour, value.minute) == (15, 30)


@pytest.mark.parametrize(
    "text",
    [
        "1403-01-01T12:00:00Z",
        "1403-01-01T15:30:00+03:30",
        "1403-01-01T15:30:00+0330",
        "۱۴۰۳-۰۱-۰۱T۱۵:۳۰:۰۰+۰۳:۳۰",
        "2024-03-20T12:00:00+00:00",
    ],
)
def test_strings_with_offsets_keep_the_instant(text):
    assert to_jalali_datetime(text) == datetime(2024, 3, 20, 12, 0, tzinfo=UTC)


def test_datetime_parser_keeps_microseconds():
    assert to_jalali_datetime("1403-01-01T12:00:00.5Z").microsecond == 500000


def test_datetime_parser_rejects_date_only_input():
    with pytest.raises(ValueError, match="must include a time"):
        to_jalali_datetime("1405-06-19")


def test_datetime_parser_rejects_plain_dates_and_garbage():
    with pytest.raises(TypeError):
        to_jalali_datetime(date(2024, 3, 20))
    with pytest.raises(ValueError):
        to_jalali_datetime("not a datetime")
    with pytest.raises(ValueError):
        to_jalali_datetime("1403-13-01 10:00")


def test_datetime_round_trip_through_jdatetime_is_lossless():
    original = datetime(2024, 3, 20, 12, 30, 45, 123456, tzinfo=UTC)
    value = to_jalali_datetime(original)
    assert to_jalali_datetime(value.togregorian()) == value
    assert value.togregorian() == original


# --- formatting -------------------------------------------------------------


def test_format_jalali_on_dates():
    assert format_jalali(date(2024, 3, 20), "%Y/%m/%d") == "1403/01/01"
    assert format_jalali(jdatetime.date(1403, 1, 1)) == "1403/01/01"


def test_format_jalali_shows_aware_datetimes_in_local_time():
    value = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)
    assert format_jalali(value, "%Y/%m/%d %H:%M") == "1403/01/01 15:30"


def test_format_jalali_supports_farsi_digits():
    assert format_jalali(date(2024, 3, 20), digits="farsi") == "۱۴۰۳/۰۱/۰۱"
    assert to_farsi_digits("1403-01-01") == "۱۴۰۳-۰۱-۰۱"
    with pytest.raises(ValueError):
        format_jalali(date(2024, 3, 20), digits="klingon")


def test_format_jalali_supports_month_and_12hour_directives():
    value = datetime(2026, 8, 27, 14, 11, 0)
    assert format_jalali(value, "%y/%b/%d %I:%M %p") == "05/شهر/05 02:11 بعد از ظهر"
    assert format_jalali(value, "%A %B") == "پنج‌شنبه شهریور"


def test_isoformat_jalali():
    assert isoformat_jalali(date(2024, 3, 20)) == "1403-01-01"
    assert isoformat_jalali(datetime(2024, 3, 20, 12, 0, tzinfo=UTC)) == (
        "1403-01-01T15:30:00+03:30"
    )
    assert isoformat_jalali(datetime(2024, 3, 20, 12, 0, 0, 5)) == (
        "1403-01-01T12:00:00.000005"
    )


# --- ranges -----------------------------------------------------------------


def test_jalali_year_range_handles_leap_years():
    # 1403 is a leap year: Esfand has 30 days, so the next year starts on the 21st.
    assert jalali_range(1403) == (date(2024, 3, 20), date(2025, 3, 21))
    assert jalali_range(1402) == (date(2023, 3, 21), date(2024, 3, 20))


def test_jalali_month_and_day_ranges():
    assert jalali_range(1403, 1) == (date(2024, 3, 20), date(2024, 4, 20))
    start, end = jalali_range(1403, 12)
    assert start == jdatetime.date(1403, 12, 1).togregorian()
    assert end == date(2025, 3, 21)
    assert jalali_range(1403, 1, 1) == (date(2024, 3, 20), date(2024, 3, 21))
    with pytest.raises(ValueError):
        jalali_range(1403, day=5)


def test_jalali_datetime_range_uses_local_midnight():
    start, end = jalali_datetime_range(1403)
    assert start == datetime(2024, 3, 19, 20, 30, tzinfo=UTC)
    assert end == datetime(2025, 3, 20, 20, 30, tzinfo=UTC)
