from datetime import date

import pytest

from jalali_suite import (
    JalaliDate,
    format_jalali,
    to_farsi_digits,
    to_gregorian,
    to_jalali,
    to_jalali_datetime,
)


def test_known_jalali_conversion():
    assert to_jalali(date(2024, 3, 20)) == JalaliDate(1403, 1, 1)


def test_round_trip_conversion():
    d = JalaliDate(1403, 1, 1)
    assert d.to_gregorian() == date(2024, 3, 20)
    assert to_jalali(d).isoformat == "1403-01-01"


def test_format_jalali():
    assert format_jalali(date(2024, 3, 20), "%Y/%m/%d") == "1403/01/01"


def test_to_gregorian_works_on_components():
    assert to_gregorian(1403, 1, 1) == date(2024, 3, 20)


def test_to_jalali_accepts_jalali_iso_strings():
    assert to_jalali("1403-01-01") == JalaliDate(1403, 1, 1)


def test_to_jalali_accepts_farsi_digits():
    assert to_jalali("۱۴۰۳-۰۱-۰۱") == JalaliDate(1403, 1, 1)


def test_format_jalali_supports_farsi_digits():
    assert format_jalali(date(2024, 3, 20), digits="farsi") == "۱۴۰۳/۰۱/۰۱"
    assert to_farsi_digits("1403-01-01") == "۱۴۰۳-۰۱-۰۱"


def test_datetime_parser_rejects_date_only_input():
    with pytest.raises(ValueError, match="must include a time"):
        to_jalali_datetime("1405-06-19")
