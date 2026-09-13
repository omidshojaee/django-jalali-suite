from datetime import date, datetime

from django import template

from ..settings import jalali_settings
from ..utils import format_jalali

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
    return format_jalali(value, digits=digits or jalali_settings.get("DIGITS"))


@register.simple_tag
def jalali_now(fmt=None):
    return format_jalali(datetime.now(), fmt)


@register.simple_tag
def jalali_date(value, fmt=None, digits=None):
    if value in (None, "") or not isinstance(value, (date, datetime)):
        return "-"
    return format_jalali(value, fmt, digits)