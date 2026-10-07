"""Conversion, parsing and formatting helpers.

Jalali values are plain :mod:`jdatetime` objects. They compare, sort, hash and
subtract against the standard library ``date``/``datetime`` types, and they keep
their ``tzinfo``. Every value that leaves the database is converted to the
*current* Django time zone, the same rule Django applies to its own
``DateTimeField``.
"""

from __future__ import annotations

import datetime as dt
import re

import jdatetime
from django.conf import settings
from django.utils import timezone
from django.utils.translation import get_language
from jdatetime import FA_LOCALE

#: Years below this value in an ISO-like string are read as Jalali, the rest as
#: Gregorian. The two ranges do not overlap for any realistic date (Jalali year
#: 1700 is Gregorian 2321), which is what makes the guess safe.
JALALI_YEAR_LIMIT = 1700

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_LATIN_TO_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_DATE_RE = re.compile(r"(\d{1,4})[-/](\d{1,2})[-/](\d{1,2})")
_DATETIME_RE = re.compile(
    r"(\d{1,4})[-/](\d{1,2})[-/](\d{1,2})"
    r"[T\s]+(\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?"
    r"\s*(Z|[+-]\d{2}:?\d{2})?"
)


def normalize_digits(value: str) -> str:
    """Convert Persian and Arabic-Indic digits to ASCII digits."""
    return value.translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)


def to_farsi_digits(value: str | int) -> str:
    return str(value).translate(_LATIN_TO_PERSIAN_DIGITS)


def uses_farsi_digits() -> bool:
    """Whether the active Django language calls for Farsi numerals."""
    return (get_language() or "").startswith("fa")


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


class JalaliDate(jdatetime.date):
    """The value of a ``JalaliDateField``: a plain ``jdatetime.date``.

    It compares, sorts and subtracts against standard dates, and it converts to
    text exactly the same way in every language (``str()`` is ISO, ``1403-01-01``),
    so logs, URLs, filenames and cache keys never depend on the active language.
    Display for people is done by the admin, forms and the ``|date``, ``|time`` and
    ``|jalali`` template filters, never by changing the value itself.

    The one difference from ``jdatetime.date``: ``f"{value}"`` works. ``jdatetime``
    formats an empty spec as an empty string.
    """

    def __format__(self, spec):
        return super().__format__(spec) if spec else str(self)


class JalaliDateTime(jdatetime.datetime):
    """The value of a ``JalaliDateTimeField``; see :class:`JalaliDate`."""

    def __format__(self, spec):
        return super().__format__(spec) if spec else str(self)


def _jdate(value) -> JalaliDate:
    if isinstance(value, JalaliDate):
        return value
    return JalaliDate(value.year, value.month, value.day)


def _jdatetime(value) -> JalaliDateTime:
    if isinstance(value, JalaliDateTime):
        return value
    return JalaliDateTime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=value.tzinfo,
    )


# ---------------------------------------------------------------------------
# Time zone helpers
# ---------------------------------------------------------------------------


def _localize(value: dt.datetime) -> dt.datetime:
    """Convert an aware datetime to the current time zone; leave naive alone."""
    if settings.USE_TZ and timezone.is_aware(value):
        return timezone.localtime(value)
    return value


def _make_aware(value: dt.datetime) -> dt.datetime:
    """Interpret a naive datetime in the current time zone (when USE_TZ)."""
    if settings.USE_TZ and timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _parse_offset(text: str) -> dt.tzinfo:
    if text == "Z":
        return dt.timezone.utc
    sign = -1 if text[0] == "-" else 1
    digits = text[1:].replace(":", "")
    delta = dt.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
    return dt.timezone(sign * delta)


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def _is_jalali_year(year: int, jalali: bool | None) -> bool:
    return jalali if jalali is not None else year < JALALI_YEAR_LIMIT


def to_jalali(value, *, jalali: bool | None = None) -> jdatetime.date:
    """Return a ``jdatetime.date`` for a date, datetime or ISO-like string.

    Strings are read as Jalali when the year is below ``JALALI_YEAR_LIMIT`` and
    as Gregorian otherwise; pass ``jalali=True`` to always read them as Jalali
    (what a Jalali form input means). Aware datetimes are converted to the
    current time zone first, so the date matches what the user sees on the wall
    clock.
    """
    if value is None:
        raise ValueError("Value cannot be None")
    if isinstance(value, jdatetime.datetime):
        return _jdate(value.date())
    if isinstance(value, jdatetime.date):
        return _jdate(value)
    if isinstance(value, dt.datetime):
        return _jdate(jdatetime.date.fromgregorian(date=_localize(value).date()))
    if isinstance(value, dt.date):
        return _jdate(jdatetime.date.fromgregorian(date=value))
    if isinstance(value, str):
        cleaned = normalize_digits(value.strip())
        # ``match`` (not ``fullmatch``) so full ISO datetimes also yield their date.
        match = _DATE_RE.match(cleaned)
        if match is None:
            raise ValueError(f"Unrecognised date: {value!r}")
        year, month, day = (int(match.group(i)) for i in (1, 2, 3))
        if _is_jalali_year(year, jalali):
            return JalaliDate(year, month, day)
        return _jdate(jdatetime.date.fromgregorian(date=dt.date(year, month, day)))
    raise TypeError(f"Unsupported value type: {type(value)!r}")


def to_jalali_datetime(value, *, jalali: bool | None = None) -> jdatetime.datetime:
    """Return a ``jdatetime.datetime`` for a datetime or ISO-like string.

    Aware values are converted to the current time zone. Strings without an
    explicit offset are read as wall-clock time in the current time zone, which
    is what a person typing into a form means.
    """
    if value is None:
        raise ValueError("Value cannot be None")
    if isinstance(value, jdatetime.datetime):
        return _jdatetime(
            jdatetime.datetime.fromgregorian(datetime=_localize(value.togregorian()))
        )
    if isinstance(value, dt.datetime):
        return _jdatetime(jdatetime.datetime.fromgregorian(datetime=_localize(value)))
    if isinstance(value, str):
        cleaned = normalize_digits(value.strip())
        if _DATE_RE.fullmatch(cleaned):
            raise ValueError(
                "A Jalali datetime must include a time in YYYY-MM-DDTHH:MM[:SS] format."
            )
        match = _DATETIME_RE.fullmatch(cleaned)
        if match is None:
            raise ValueError(f"Unrecognised datetime: {value!r}")
        year, month, day, hour, minute = (int(match.group(i)) for i in range(1, 6))
        second = int(match.group(6) or 0)
        microsecond = int((match.group(7) or "")[:6].ljust(6, "0"))
        if _is_jalali_year(year, jalali):
            gregorian = jdatetime.datetime(
                year, month, day, hour, minute, second, microsecond
            ).togregorian()
        else:
            gregorian = dt.datetime(
                year, month, day, hour, minute, second, microsecond
            )
        offset = match.group(8)
        if offset:
            gregorian = gregorian.replace(tzinfo=_parse_offset(offset))
        else:
            gregorian = _make_aware(gregorian)
        return _jdatetime(
            jdatetime.datetime.fromgregorian(datetime=_localize(gregorian))
        )
    if isinstance(value, dt.date):
        raise TypeError("A date without a time cannot be converted to a datetime.")
    raise TypeError(f"Unsupported value type: {type(value)!r}")


def to_gregorian(year: int, month: int = 1, day: int = 1) -> dt.date:
    return jdatetime.date(year, month, day).togregorian()


def to_gregorian_value(value):
    """Return the Gregorian equivalent of a jdatetime value (others unchanged)."""
    if isinstance(value, jdatetime.datetime):
        return value.togregorian()
    if isinstance(value, jdatetime.date):
        return value.togregorian()
    return value


def date2jalali(g_date):
    """django-jalali-date compatible: like :func:`to_jalali`, but ``None`` -> ``None``."""
    return None if g_date is None else to_jalali(g_date)


def datetime2jalali(g_date):
    """django-jalali-date compatible: like :func:`to_jalali_datetime`, ``None`` -> ``None``."""
    return None if g_date is None else to_jalali_datetime(g_date)


# ---------------------------------------------------------------------------
# Ranges
# ---------------------------------------------------------------------------


def jalali_range(year: int, month: int | None = None, day: int | None = None):
    """Half-open Gregorian ``(start, end)`` dates for a Jalali year/month/day.

    Month and day lookups cannot be expressed portably in SQL, so filter with
    ``field__gte=start, field__lt=end`` instead. Use :func:`jalali_datetime_range`
    for ``DateTimeField`` columns.
    """
    if month is None:
        if day is not None:
            raise ValueError("day requires month")
        start = jdatetime.date(year, 1, 1)
        end = jdatetime.date(year + 1, 1, 1)
    elif day is None:
        start = jdatetime.date(year, month, 1)
        end = (
            jdatetime.date(year + 1, 1, 1)
            if month == 12
            else jdatetime.date(year, month + 1, 1)
        )
    else:
        start = jdatetime.date(year, month, day)
        end = start + dt.timedelta(days=1)
    return start.togregorian(), end.togregorian()


def jalali_datetime_range(year: int, month: int | None = None, day: int | None = None):
    """Like :func:`jalali_range` but as midnight datetimes in the current time zone."""
    start, end = jalali_range(year, month, day)
    return (
        _make_aware(dt.datetime.combine(start, dt.time())),
        _make_aware(dt.datetime.combine(end, dt.time())),
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def isoformat_jalali(value) -> str:
    """ISO-8601-style Jalali string: ``1403-01-01`` or ``1403-01-01T12:30:00+03:30``."""
    if isinstance(value, (dt.datetime, jdatetime.datetime)):
        jvalue = to_jalali_datetime(value)
        text = jvalue.strftime("%Y-%m-%dT%H:%M:%S")
        if jvalue.microsecond:
            text += f".{jvalue.microsecond:06d}"
        offset = jvalue.utcoffset()
        if offset is not None:
            total = int(offset.total_seconds() // 60)
            sign = "-" if total < 0 else "+"
            hours, minutes = divmod(abs(total), 60)
            text += f"{sign}{hours:02d}:{minutes:02d}"
        return text
    return to_jalali(value).strftime("%Y-%m-%d")


def format_jalali(value, fmt: str | None = None, digits: str | None = None) -> str:
    """Format a date or datetime as a Jalali string.

    Aware datetimes are shown in the current time zone. ``digits`` is
    ``"latin"`` or ``"farsi"`` and defaults to the active language.
    """
    from .settings import jalali_settings

    digits = digits or ("farsi" if uses_farsi_digits() else "latin")
    if digits not in ("latin", "farsi"):
        raise ValueError("digits must be 'latin' or 'farsi'")

    if isinstance(value, (dt.datetime, jdatetime.datetime)):
        fmt = fmt or jalali_settings.get("DATETIME_FORMAT")
        jvalue = to_jalali_datetime(value)
        formatter = jdatetime.datetime(
            jvalue.year,
            jvalue.month,
            jvalue.day,
            jvalue.hour,
            jvalue.minute,
            jvalue.second,
            jvalue.microsecond,
            tzinfo=jvalue.tzinfo,
            locale=FA_LOCALE,
        )
    else:
        fmt = fmt or jalali_settings.get("DATE_FORMAT")
        jvalue = to_jalali(value)
        formatter = jdatetime.date(
            jvalue.year, jvalue.month, jvalue.day, locale=FA_LOCALE
        )

    result = formatter.strftime(fmt)
    return to_farsi_digits(result) if digits == "farsi" else result
