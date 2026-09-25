from datetime import date, datetime

from django import template

from ..utils import JalaliDate, JalaliDateTime, format_jalali

register = template.Library()


@register.filter
def jalali(value, fmt=None):
    if value in (None, ""):
        return "-"
    return format_jalali(value, fmt)


@register.filter
def jalali_digits(value, digits=None):
    if value in (None, ""):
        return "-"
    return format_jalali(value, digits=digits)


@register.simple_tag
def jalali_now(fmt=None):
    return format_jalali(datetime.now(), fmt)


@register.simple_tag
def jalali_date(value, fmt=None, digits=None):
    if value in (None, "") or not isinstance(
        value, (date, datetime, JalaliDate, JalaliDateTime)
    ):
        return "-"
    return format_jalali(value, fmt, digits)