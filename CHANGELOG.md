# Changelog

## 4.0.0

A breaking release that makes the package a drop-in replacement for
django-jalali and django-jalali-date.

### Breaking

- `JalaliDate` / `JalaliDateTime` are now thin subclasses of `jdatetime.date` / `jdatetime.datetime`. The old dataclass members are gone: use `.togregorian()` and `isoformat_jalali()`.
- Model fields return `jdatetime` values that compare, sort, hash and subtract against standard `date` / `datetime`, and keep their time zone. Assignment is normalised, so an attribute has the same type before and after saving.
- Form and serializer fields clean to standard `date` / aware `datetime` (they used to return the suite's own value objects).
- `to_jalali()` no longer accepts integer timestamps (the result depended on the machine's time zone).
- Requires `jdatetime>=6.1.0`.

### Principles

- A value never depends on the language: `str()` is ISO in every language. Only what the package displays (admin, widgets, its template filters and tags) follows the language, with Persian month names and, under `fa`, Persian digits.
- The package replaces none of Django's own filters or settings. Django's `|date` / `|time` do not know the Jalali calendar (see the README); use `|jalali` and `{% jalali_date %}`.
- The admin mixin acts on the Jalali fields you declare. Plain Django date fields are left alone unless you set `jalali_widgets_for_gregorian_fields = True` on an admin.
- Fixed an upstream `jdatetime` bug: `f"{jdate}"` returned an empty string.

### Fixed

- Time zones: values are shown and edited in the current time zone and typed wall-clock time is saved as that local instant. Previously UTC wall-clock time was shown, and typed local time was stored as UTC, whenever `TIME_ZONE` was not UTC.
- `JalaliDateTimeField.get_prep_value` now goes through Django's naive-datetime handling and warning.
- The split date/time form field always reported "changed", which made admin inlines save untouched extra rows.
- `input_formats` on the date form field was accepted but ignored.
- `JalaliDateFieldListFilter` was never registered and offered no choices; it is now registered for the suite's fields and uses Jalali month and year boundaries.
- The admin mixin no longer mutates the admin instance on every request.
- `{% jalali_now %}` respects the current time zone.

### Added

- `__year` (with `__gt`, `__gte`, `__lt`, `__lte`) and `__date` lookups on the Jalali calendar; `__month`, `__day`, `__quarter` raise `FieldError` instead of silently using the Gregorian calendar.
- `jalali_range()` and `jalali_datetime_range()`, `isoformat_jalali()`.
- Admin: Jalali widgets for plain Django `DateField` / `DateTimeField`; Jalali read-only fields; sortable Jalali list columns; `JalaliDateTabularInline` / `JalaliDateStackedInline`; `LIST_DISPLAY_AUTO_CONVERT` setting.
- Admin `date_hierarchy` that drills down by Jalali year, month and day (Django's own would filter on Gregorian numbers), with the `jalali_suite.W001` system check for admins that miss the mixin.
- `jalali_suite.query.jalali_dates()`, a Jalali replacement for `QuerySet.dates()` / `datetimes()`.
- A single-input datetime widget, `input_date_formats` / `input_time_formats` on the split field.
- Compatibility names from django-jalali and django-jalali-date (see the README migration section).
- Django 6.0 and 6.1 support; CI for Python 3.10 to 3.14.
