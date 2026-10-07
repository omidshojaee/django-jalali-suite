"""Jalali calendar support for Django."""

__version__ = "4.0.0"

from .utils import (
    JalaliDate,
    JalaliDateTime,
    date2jalali,
    datetime2jalali,
    format_jalali,
    isoformat_jalali,
    jalali_datetime_range,
    jalali_range,
    normalize_digits,
    to_farsi_digits,
    to_gregorian,
    to_jalali,
    to_jalali_datetime,
)

__all__ = [
    "JalaliDate",
    "JalaliDateTime",
    "date2jalali",
    "datetime2jalali",
    "format_jalali",
    "isoformat_jalali",
    "jalali_datetime_range",
    "jalali_range",
    "normalize_digits",
    "to_farsi_digits",
    "to_gregorian",
    "to_jalali",
    "to_jalali_datetime",
]
