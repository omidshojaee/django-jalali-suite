# django-jalali-suite

A Django utility package for Persian/Jalali calendar conversion, formatting, and model/form integrations.

django-jalali-suite helps you work with Jalali dates inside Django applications without needing to reimplement conversion logic or manually manage Persian date formatting. It gives you a simple API for conversion, formatting, and basic field/widget support.

## Features

- Jalali <-> Gregorian conversion
- Jalali date formatting helpers like `format_jalali()`
- Data-class based Jalali date values
- Django form field support
- Django model field support
- Django admin compatibility for Jalali date entry and display
- Reusable admin mixin with a Jalali datepicker
- Custom widget and static CSS/JavaScript assets for Jalali date inputs
- Farsi and Arabic-Indic digit input support
- Persian datepicker labels and Farsi digit rendering
- Persian-friendly `Vazirmatn` font fallback
- Clean integration with Python and Django projects

## Installation

Install from PyPI:

```bash
pip install django-jalali-suite
```

Or install from the source tree:

```bash
git clone https://github.com/omidshojaee/django-jalali-suite.git
cd django-jalali-suite
python -m pip install -e .
```

For Django REST Framework support, install the optional dependency:

```bash
python -m pip install django-jalali-suite[drf]
```

Add the package to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... your Django apps
    "jalali_suite",
]
```

This enables the package's template tags, widget templates, and static assets.

## Quick start

```python
from datetime import date
from jalali_suite import JalaliDate, format_jalali, to_gregorian, to_jalali

# Gregorian to Jalali
jalali = to_jalali(date(2024, 3, 20))
print(jalali)  # JalaliDate(year=1403, month=1, day=1)
print(jalali.isoformat)  # 1403-01-01

# Jalali to Gregorian
print(to_gregorian(1403, 1, 1))  # 2024-03-20

# Formatting
print(format_jalali(date(2024, 3, 20), "%Y/%m/%d"))  # 1403/01/01
```

## Django usage

### Forms

```python
from django import forms
from jalali_suite.forms import JalaliDateField

class ExampleForm(forms.Form):
    birthday = JalaliDateField()
```

This converts values from Gregorian ISO strings into Jalali date objects when cleaning form data. Render `{{ form.media }}` in the page `<head>` to load the datepicker assets and bundled Vazirmatn font.

### Models

```python
from django.db import models
from jalali_suite.models import JalaliDateField, JalaliDateTimeField

class Person(models.Model):
    birthday = JalaliDateField()
    created_at = JalaliDateTimeField()
```

These fields store standard Gregorian date and datetime values in the database while exposing Jalali values in Python. `JalaliDateTimeField` uses a split Admin widget: the date portion receives the Jalali datepicker and the time portion remains a normal time input.

### Django Admin

The admin integration is provided by `JalaliDateAdminMixin`. It adds the Jalali date widget to `JalaliDateField` and the split Jalali datetime widget to `JalaliDateTimeField`, and loads the datepicker CSS and JavaScript assets.

Use the mixin before Django's `ModelAdmin`:

```python
from django.contrib import admin
from jalali_suite.admin import JalaliDateAdminMixin
from .models import Person

@admin.register(Person)
class PersonAdmin(JalaliDateAdminMixin, admin.ModelAdmin):
    list_display = ["id", "birthday"]
```

Or use the convenience class:

```python
from jalali_suite.admin import JalaliDateModelAdmin

@admin.register(Person)
class PersonAdmin(JalaliDateModelAdmin):
    list_display = ["id", "birthday"]
```

The datepicker opens when a Jalali date field receives focus, supports month navigation, renders Persian month names and Farsi digits, and writes a Jalali value such as `۱۴۰۳-۰۱-۰۱` back into the form field. The backend accepts Persian, Arabic-Indic, and Latin digits. No third-party JavaScript dependency is required.

The package bundles Vazirmatn Regular under its SIL OFL license. Admin media always loads the bundled font, so the widget works offline and does not require external font requests.

This is especially useful for:

- admin forms for Persian users
- date-based filtering in admin views
- record entry screens where Jalali dates are expected by business users
- making the admin experience feel native to Persian calendar workflows

## Why django-jalali-suite

The package brings the full Jalali date workflow into one Django-native API:

- conversion helpers and immutable Jalali values
- Jalali-aware forms and model fields
- Gregorian database storage with Jalali values in Python
- admin widgets and a bundled Persian datepicker
- Farsi and Arabic-Indic digit support
- no additional JavaScript framework or calendar package required

The widget and datepicker layers are implemented and maintained inside this package. This keeps installation, configuration, and versioning in one place while allowing applications to use Jalali dates consistently across Python code, forms, models, and Django admin.

## API reference

### `JalaliDate`

A simple immutable value object representing a Jalali date.

```python
from jalali_suite import JalaliDate

value = JalaliDate(1403, 1, 1)
print(value.isoformat)
print(value.to_gregorian())
```

### `to_jalali(value)`

Converts a Gregorian date, datetime, string, or Unix timestamp to a Jalali date object.

### `to_gregorian(year, month, day)`

Converts Jalali year/month/day to a Gregorian `date` value.

### `format_jalali(value, fmt="%Y/%m/%d")`

Formats a date-like input in Jalali format using a strftime-style token set. Pass `digits="farsi"` when the output should use Persian digits.

## Configuration

Override project behavior with `JALALI_SUITE`:

```python
JALALI_SUITE = {
    "DIGITS": "farsi",  # "latin" or "farsi"
    "DATE_FORMAT": "%Y/%m/%d",
    "DATETIME_FORMAT": "%Y/%m/%d %H:%M:%S",
    "ADMIN_AUTO_CONVERT_LIST_DISPLAY": False,
}
```

Load template support with `{% load jalali_suite %}` and use the `jalali`,
`jalali_digits`, and `jalali_now` filters/tags.

## Django REST Framework

Use `JalaliModelSerializer` to automatically represent
`JalaliDateField` and `JalaliDateTimeField` values as Jalali ISO strings and
accept Latin, Persian, or Arabic-Indic digits:

```python
from jalali_suite.serializers import JalaliModelSerializer

class PersonSerializer(JalaliModelSerializer):
    class Meta:
        model = Person
        fields = ("birthday", "created_at")
```

The lower-level `JalaliDateSerializerField` and
`JalaliDateTimeSerializerField` are also available for custom serializers.

## Development

```bash
git clone https://github.com/omidshojaee/django-jalali-suite.git
cd django-jalali-suite
python -m pip install -e .[dev]
pytest
```

## License

MIT © Omid Shojaee

## Author

- Omid Shojaee
- Email: omid.shojaee@gmail.com
- GitHub: https://github.com/omidshojaee
