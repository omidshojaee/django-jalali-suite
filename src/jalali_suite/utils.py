from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from jdatetime import date as JDate
from jdatetime import datetime as JDateTime

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_LATIN_TO_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def normalize_digits(value: str) -> str:
    return value.translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)


def to_farsi_digits(value: str | int) -> str:
    return str(value).translate(_LATIN_TO_PERSIAN_DIGITS)


@dataclass(frozen=True)
class JalaliDate:
    year: int
    month: int
    day: int

    def __post_init__(self):
        JDate(self.year, self.month, self.day)

    @property
    def isoformat(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def to_gregorian(self) -> dt.date:
        return to_gregorian(self.year, self.month, self.day)


@dataclass(frozen=True)
class JalaliDateTime:
    year: int
    month: int
    day: int
    hour: int = 0
    minute: int = 0
    second: int = 0
    microsecond: int = 0

    def __post_init__(self):
        JDateTime(
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
            self.microsecond,
        )

    @property
    def isoformat(self) -> str:
        value = f"{self.year:04d}-{self.month:02d}-{self.day:02d}T{self.hour:02d}:{self.minute:02d}:{self.second:02d}"
        return f"{value}.{self.microsecond:06d}" if self.microsecond else value

    def to_datetime(self) -> dt.datetime:
        gregorian = JDateTime(
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
            self.microsecond,
        ).togregorian()
        return gregorian


def to_jalali(
    value: dt.date | dt.datetime | JalaliDate | str | int | None,
) -> JalaliDate:
    if value is None:
        raise ValueError("Value cannot be None")
    if isinstance(value, JalaliDate):
        return value
    if isinstance(value, dt.datetime):
        value = value.date()
    elif isinstance(value, str):
        cleaned = normalize_digits(value.strip()).replace("/", "-")
        if "T" in cleaned:
            cleaned = cleaned.split("T", 1)[0]
        if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", cleaned):
            year, month, day = map(int, cleaned.split("-"))
            if year < 1700:
                return JalaliDate(year, month, day)
        value = dt.date.fromisoformat(cleaned)
    elif isinstance(value, int):
        value = dt.date.fromtimestamp(value)
    if not isinstance(value, dt.date):
        raise TypeError(f"Unsupported value type: {type(value)!r}")
    jdate = JDate.fromgregorian(date=value)
    return JalaliDate(jdate.year, jdate.month, jdate.day)


def to_jalali_datetime(value: dt.datetime | str) -> JalaliDateTime:
    if isinstance(value, str):
        cleaned = normalize_digits(value.strip()).replace("T", " ")
        if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", cleaned):
            raise ValueError(
                "A Jalali datetime must include a time in YYYY-MM-DDTHH:MM[:SS] format."
            )
        match = re.fullmatch(
            r"(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.(\d+))?",
            cleaned,
        )
        if match and int(match.group(1)) < 1700:
            year, month, day, hour, minute = (
                int(match.group(index)) for index in range(1, 6)
            )
            second = int(match.group(6) or 0)
            microsecond = int((match.group(7) or "")[:6].ljust(6, "0") or 0)
            return JalaliDateTime(year, month, day, hour, minute, second, microsecond)
        value = dt.datetime.fromisoformat(cleaned)
    if not isinstance(value, dt.datetime):
        raise TypeError(f"Unsupported value type: {type(value)!r}")
    jvalue = JDateTime.fromgregorian(datetime=value)
    return JalaliDateTime(
        jvalue.year,
        jvalue.month,
        jvalue.day,
        jvalue.hour,
        jvalue.minute,
        jvalue.second,
        jvalue.microsecond,
    )


def to_gregorian(year: int, month: int = 1, day: int = 1) -> dt.date:
    return JDate(year, month, day).togregorian()


def format_jalali(value, fmt: str | None = None, digits: str | None = None) -> str:
    from .settings import jalali_settings

    digits = digits or jalali_settings.get("DIGITS")
    if isinstance(value, (dt.datetime, JalaliDateTime)):
        fmt = fmt or jalali_settings.get("DATETIME_FORMAT")
        jalali = (
            to_jalali_datetime(value)
            if not isinstance(value, JalaliDateTime)
            else value
        )
        result = fmt.replace("%Y", f"{jalali.year:04d}").replace(
            "%y", f"{jalali.year % 100:02d}"
        )
        result = result.replace("%m", f"{jalali.month:02d}").replace(
            "%d", f"{jalali.day:02d}"
        )
        result = (
            result.replace("%H", f"{jalali.hour:02d}")
            .replace("%M", f"{jalali.minute:02d}")
            .replace("%S", f"{jalali.second:02d}")
        )
    else:
        fmt = fmt or jalali_settings.get("DATE_FORMAT")
        jalali = to_jalali(value)
        result = fmt.replace("%Y", f"{jalali.year:04d}").replace(
            "%y", f"{jalali.year % 100:02d}"
        )
        result = result.replace("%m", f"{jalali.month:02d}").replace(
            "%d", f"{jalali.day:02d}"
        )
    if digits == "farsi":
        return to_farsi_digits(result)
    if digits != "latin":
        raise ValueError("digits must be 'latin' or 'farsi'")
    return result
