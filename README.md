# django-jalali-suite

Jalali (Persian) calendar support for Django: model fields, forms, admin, template
filters and Django REST Framework fields in one package.

The database always holds ordinary Gregorian `date` / `timestamptz` columns. Python
code sees [`jdatetime`](https://pypi.org/project/jdatetime/) values that compare,
sort and subtract against standard `date` / `datetime` objects, keep their time
zone, and agree with Django about local time.

It is designed as a single replacement for
[django-jalali](https://github.com/slashmili/django-jalali) +
[django-jalali-date](https://github.com/a-roomana/django-jalali-date); see
[Migrating](#migrating-from-django-jalali-and-django-jalali-date).

## The rule it follows

You decide which fields are Jalali: declare them as `JalaliDateField` /
`JalaliDateTimeField` (or subclass a built-in field into one, as you would for
`last_login`). With `LANGUAGE_CODE = "fa"`, those fields are Jalali wherever the
package shows them, with Persian month names (فروردین، اردیبهشت، ...) and Persian digits:

- **in the admin**: inputs and datepicker, list columns, read-only values, filters, `date_hierarchy`
- **in forms**: the same datepicker widget
- **in templates**: the tags and filters the package provides (`jalali`, `jalali_date`, ...)

Nothing else changes. Ordinary Django date fields, the admin history page and every other
page stay exactly as Django renders them, and the package overrides none of Django's own
filters or settings. A value never depends on the language either: `str(value)` is the
ISO string in every language. Only what the package *displays* follows the language.

## Features

- **Model fields** `JalaliDateField` / `JalaliDateTimeField` returning `jdatetime` values, with a type that is the same whether an instance was just created or loaded from the database
- **Time-zone correct**: aware values are shown and edited in the current Django time zone; typed wall-clock time is saved as that local instant
- **Query lookups**: `__year` (and `__year__gt/gte/lt/lte`) in the Jalali calendar, plus `jalali_range()` helpers for months and days
- **Forms**: Jalali date, datetime and split date+time fields that clean to standard Gregorian values
- **Admin**: Jalali datepicker widgets, Jalali list columns that stay sortable, read-only values, a Jalali date filter, Jalali `date_hierarchy`, inline support
- **Templates**: the `jalali`, `jalali_digits`, `jalali_now`, `jalali_date` filters and tags (and `jformat` / `to_jalali` aliases)
- **Django REST Framework** serializer fields and `JalaliModelSerializer`
- Persian / Arabic-Indic digit input and Farsi digit output, bundled Vazirmatn font, no JavaScript framework

## Installation

```bash
pip install django-jalali-suite            # core
pip install "django-jalali-suite[drf]"     # with Django REST Framework support
```

```python
INSTALLED_APPS = [
    # ...
    "jalali_suite",
]
```

Requires Python 3.10+, Django 5.2+ and `jdatetime` 6.1+.

## Quick start

```python
from datetime import date
from jalali_suite import format_jalali, to_gregorian, to_jalali

to_jalali(date(2024, 3, 20))                    # jdatetime.date(1403, 1, 1)
to_gregorian(1403, 1, 1)                        # datetime.date(2024, 3, 20)
format_jalali(date(2024, 3, 20), "%Y/%m/%d")    # '1403/01/01'
format_jalali(date(2024, 3, 20), digits="farsi")  # '۱۴۰۳/۰۱/۰۱'
```

## Models

```python
from django.db import models
from jalali_suite.models import JalaliDateField, JalaliDateTimeField

class Person(models.Model):
    birthday = JalaliDateField()
    created_at = JalaliDateTimeField(auto_now_add=True)
```

```python
person = Person.objects.get(pk=1)
person.birthday              # jdatetime.date(1403, 1, 1)
person.birthday == date(2024, 3, 20)         # True
person.created_at < timezone.now()           # True  (aware, current time zone)
timezone.now() - person.created_at           # a timedelta
person.birthday = "1403-02-15"               # strings, dates, datetimes all work
```

Every assignment — constructor arguments, `default=`, `auto_now`, forms,
`refresh_from_db()` — is normalised to a `jdatetime` object, so an attribute never
changes type between "fresh" and "loaded".

**Time zones.** With `USE_TZ = True` an aware value is converted to the *current*
time zone when read, exactly as Django does for its own `DateTimeField`. A Jalali
string without an offset (`"1403-01-01 15:30"`) means local wall-clock time. Naive
`datetime` objects keep Django's usual behaviour: they are interpreted in the
default time zone and Django's `RuntimeWarning` is raised.

**Serialization.** `dumpdata`/`loaddata` use Gregorian ISO strings, so fixtures do
not depend on this package.

### Querying

```python
Person.objects.filter(birthday=jdatetime.date(1403, 1, 1))
Person.objects.filter(birthday="1403-01-01")           # Jalali string
Person.objects.filter(birthday__gte=date(2024, 3, 20))  # Gregorian works too

Person.objects.filter(birthday__year=1403)              # Jalali year
Person.objects.filter(birthday__year__gte=1400)
Person.objects.filter(created_at__date="1403-01-01")    # local Jalali date of a datetime
Person.objects.filter(created_at__date__year=1403)
```

`__year` is answered with a half-open Gregorian range, so it works on every database
and can use an index. **`__month`, `__day` and `__quarter` raise `FieldError`**
instead of silently using the Gregorian calendar; use a range:

```python
from jalali_suite import jalali_datetime_range, jalali_range

start, end = jalali_range(1403, 7)             # Mehr 1403, as Gregorian dates
Person.objects.filter(birthday__gte=start, birthday__lt=end)

start, end = jalali_datetime_range(1403, 7)    # local-midnight datetimes
Event.objects.filter(at__gte=start, at__lt=end)
```

### Where Django still uses the Gregorian calendar

Django's own calendar functions know nothing about Jalali dates and always use the
Gregorian calendar, even on Jalali fields: `ExtractYear` / `ExtractMonth` /
`ExtractDay`, `TruncYear` / `TruncMonth`, `QuerySet.dates()` and
`QuerySet.datetimes()`. They return no error, so do not use them for Jalali grouping.
Use `jalali_dates()` instead of `dates()` / `datetimes()`:

```python
from jalali_suite.query import jalali_dates

jalali_dates(Order.objects.all(), "created_at", "year")
# [jdatetime.date(1402, 1, 1), jdatetime.date(1403, 1, 1)]
jalali_dates(Order.objects.filter(...), "created_at", "month")   # month starts
```

It works for Jalali fields and plain Django date/datetime fields (datetimes are read
in the current time zone).

## Forms

```python
from django import forms
from jalali_suite.forms import JalaliDateField, SplitJalaliDateTimeField

class EventForm(forms.Form):
    day = JalaliDateField()
    at = SplitJalaliDateTimeField()
```

Input may use Latin, Persian or Arabic-Indic digits and `-` or `/` separators. Input
is always read as Jalali. Fields **clean to standard values** — `datetime.date` and
an aware `datetime.datetime` — so they work with any model field, including plain
Django ones. `ModelForm`s for the suite's model fields use these fields
automatically. Render `{{ form.media }}` in the page head to load the datepicker and
bundled font.

## Django admin

```python
from django.contrib import admin
from jalali_suite.admin import JalaliDateModelAdmin

@admin.register(Person)
class PersonAdmin(JalaliDateModelAdmin):
    list_display = ["id", "birthday", "created_at"]
    list_filter = ["birthday"]
```

or add the mixin to your own admin class: `class PersonAdmin(JalaliDateAdminMixin, admin.ModelAdmin)`.

What you get:

- the Jalali datepicker for date fields and a split date + time widget for datetime fields
- **list columns and read-only fields shown as Jalali text** (list columns remain sortable); switch off with `LIST_DISPLAY_AUTO_CONVERT`
- a Jalali date filter (Today, Past 7 days, This month, This year using Jalali month and year boundaries), applied automatically to the suite's fields
- **`date_hierarchy` drill-down by Jalali year, month and day**, in the right time zone, for the suite's fields and plain Django date columns alike. Django's own hierarchy would filter on Gregorian numbers, so a system check (`jalali_suite.W001`) warns if an admin uses a Jalali field with `date_hierarchy` but no `JalaliDateAdminMixin`. If you set your own `change_list_template`, put `{% load jalali_suite %}{% jalali_date_hierarchy cl %}` in its `date_hierarchy` block. Opt out with `jalali_date_hierarchy = False`
- plain Django `DateField` / `DateTimeField` columns are **left alone**. To get the same treatment for them on one admin (for example when moving from django-jalali-date), set `jalali_widgets_for_gregorian_fields = True` on it; the date filter is then used explicitly: `list_filter = [("created", JalaliDateFieldListFilter)]`
- inline support: `JalaliDateTabularInline`, `JalaliDateStackedInline`, or the mixin on your own inline

The datepicker needs no third-party JavaScript. Vazirmatn Regular is bundled
(SIL OFL), so nothing is fetched from external servers.

## Templates

Display a Jalali value with the package's filters and tags, after `{% load jalali_suite %}`.
With `fa` active they write Persian month names and digits:

```django
{% load jalali_suite %}
{{ order.created|jalali }}                    {# ۱۴۰۳/۰۱/۰۱ ۱۵:۳۰:۰۰  (JALALI_SUITE format) #}
{{ order.created|jalali:"%d %B %Y" }}         {# ۰۱ فروردین ۱۴۰۳       (strftime format) #}
{{ order.created|jalali:"%A" }}               {# چهارشنبه #}
{{ order.created|jalali_digits:"farsi" }}
{% jalali_date order.created "%d %B %Y" %}
{% jalali_now "%Y/%m/%d" %}
```

**Django's own `|date` and `|time` filters do not know the Jalali calendar.** On a Jalali
value they print a Gregorian month name next to a Jalali year (for example "ژانویه ۱۴۰۳")
and number weekdays from the wrong day. The package does not change Django's filters;
use `|jalali` / `{% jalali_date %}` for Jalali fields, and keep `|date` for ordinary dates.
A bare `{{ order.created }}` prints the ISO value (`1403-01-01`) in every language.

Aware datetimes are shown in the current time zone. Digits follow the active
language (Farsi digits when it starts with `fa`); override per call with `digits=`.
`jformat` and `to_jalali` are accepted as aliases of `jalali`.

## Django REST Framework

```python
from jalali_suite.serializers import JalaliModelSerializer

class PersonSerializer(JalaliModelSerializer):
    class Meta:
        model = Person
        fields = ("birthday", "created_at")
```

- **Output** is Jalali ISO: `"1403-01-01"` and `"1403-01-01T15:30:00+03:30"` (local time, with offset).
- **Input** accepts Jalali strings (Latin, Persian or Arabic-Indic digits) **and Gregorian ISO strings**: a year below 1700 is read as Jalali, anything else as Gregorian, so `2024-03-20` is never misread as the Jalali year 2024. Values with an offset (`Z`, `+03:30`) keep their instant; without one they are local time.
- `validated_data` holds standard `date` / aware `datetime` objects.
- A datetime must include a time; date-only strings belong in `JalaliDateField`.
- `JalaliDateSerializerField` / `JalaliDateTimeSerializerField` can be used on plain Django columns.

## Configuration

```python
JALALI_SUITE = {
    "DATE_FORMAT": "%Y/%m/%d",
    "DATETIME_FORMAT": "%Y/%m/%d %H:%M:%S",
    "LIST_DISPLAY_AUTO_CONVERT": True,  # Jalali text for admin list and read-only date fields
}
```

## Migrating from django-jalali and django-jalali-date

| You used | Use now |
|---|---|
| `django_jalali.db.models.jDateField` / `jDateTimeField` | `jalali_suite.models.JalaliDateField` / `JalaliDateTimeField` (aliases `jDateField`, `jDateTimeField`) |
| `django_jalali.admin.filters.JDateFieldListFilter` | `jalali_suite.admin.JalaliDateFieldListFilter` (alias `JDateFieldListFilter`) |
| `jalali_date.admin.ModelAdminJalaliMixin` | `jalali_suite.admin.JalaliDateAdminMixin` (alias `ModelAdminJalaliMixin`) |
| `TabularInlineJalaliMixin`, `StackedInlineJalaliMixin` | `JalaliDateTabularInline`, `JalaliDateStackedInline` (aliases for the mixin names exist) |
| `django_jalali.db.models.jManager` / `jQuerySet` | not needed; `__year` and `__date` work with the default manager (`jManager` / `jQuerySet` are importable aliases of Django's `Manager` / `QuerySet`) |
| `django_jalali.forms.jDateField` / `jDateTimeField` / `jDateInput` / `jDateTimeInput` | `jalali_suite.forms` and `jalali_suite.widgets`, same alias names |
| `django_jalali.serializers.serializerfield.JDateField` / `JDateTimeField` | `jalali_suite.serializers` (same alias names) |
| `jalali_date.fields.JalaliDateField`, `SplitJalaliDateTimeField` | `jalali_suite.forms.JalaliDateField`, `SplitJalaliDateTimeField` (takes `input_date_formats` / `input_time_formats`) |
| `jalali_date.widgets.AdminJalaliDateWidget`, `AdminSplitJalaliDateTime` | `jalali_suite.widgets.AdminJalaliDateWidget`, `AdminJalaliSplitDateTimeWidget` (alias `AdminSplitJalaliDateTime`) |
| `{{ v\|jformat:"..." }}` | same filter, after `{% load jalali_suite %}`; renders `""` for empty values as before |
| `{{ v\|to_jalali:"..." }}`, `{% jalali_now %}` | same, rendering `-` for empty values as before; `jalali_now` now respects the time zone |
| `jalali_admin_safe_readonly` filter and the `jalali_*` admin templates | not needed: read-only date fields are shown as Jalali by the admin mixin itself |
| `datetime2jalali()`, `date2jalali()` | same names in `jalali_suite`; `None` in, `None` out |

Settings:

| You set | Use now |
|---|---|
| `JALALI_DATE_DEFAULTS["LIST_DISPLAY_AUTO_CONVERT"]` (default `False`) | `JALALI_SUITE["LIST_DISPLAY_AUTO_CONVERT"]` (default **`True`**); also controls read-only fields |
| `JALALI_DATE_DEFAULTS["Strftime"]["date"]` / `["datetime"]` | `JALALI_SUITE["DATE_FORMAT"]` / `["DATETIME_FORMAT"]` |
| `JALALI_DATE_DEFAULTS["Static"]`, `JALALI_SETTINGS["ADMIN_JS_STATIC_FILES"]` / `["ADMIN_CSS_STATIC_FILES"]` | **not supported**: the package ships its own datepicker (the django-jalali one used jQuery UI). Subclass the widgets and override `Media` to use another one |

Things to know when switching:

- **Migrations.** Existing migrations that reference `django_jalali.db.models.jDateField` must be edited to `jalali_suite.models.JalaliDateField`. No schema change is needed: the columns are the same.
- **Lookups.** `__year` and `__date` work on the Jalali calendar (no custom manager needed). `__month`, `__day` and `__quarter` raise `FieldError`, as `__month` etc. also do in django-jalali; use `jalali_range()` with `__gte`/`__lt`.
- **Form field return types.** Form fields return Gregorian `date` / aware `datetime` (as django-jalali-date does) so they work with any model field. django-jalali's `jDateField` form field returned a `jdatetime.date`; code that reads `cleaned_data` directly and relied on that should call `to_jalali()`. Saving through a `ModelForm` is unaffected.
- **Date-only datetimes.** A datetime serializer or form input must include a time; django-jalali's `JDateTimeField` serializer also accepted a bare date.
- **Plain date fields.** django-jalali-date's mixin put Jalali widgets on every date field. Here only the suite's own fields get them; add `jalali_widgets_for_gregorian_fields = True` to an admin to keep the old behaviour.
- **List columns on by default.** Unlike django-jalali-date, the admin mixin converts the Jalali fields' list columns and read-only values unless you set `LIST_DISPLAY_AUTO_CONVERT` to `False`.
- Remove `django_jalali` / `jalali_date` from `INSTALLED_APPS` and add `jalali_suite`.

## Development

```bash
git clone https://github.com/omidshojaee/django-jalali-suite.git
cd django-jalali-suite
python -m pip install -e ".[dev]"
pytest
```

The test project runs with `TIME_ZONE = "Asia/Tehran"` on purpose.

## License

MIT © Omid Shojaee
