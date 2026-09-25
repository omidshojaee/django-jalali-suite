from datetime import date, datetime

from django import forms
from django.contrib import admin
from django.db import models

from jalali_suite.admin import JalaliDateAdminMixin
from jalali_suite.forms import JalaliDateField, SplitJalaliDateTimeField
from jalali_suite.models import JalaliDateField as ModelJalaliDateField
from jalali_suite.models import JalaliDateTimeField as ModelJalaliDateTimeField
from jalali_suite.utils import JalaliDateTime, to_jalali
from jalali_suite.widgets import JalaliSplitDateTimeWidget


class DemoForm(forms.Form):
    jalali_date = JalaliDateField()


def test_form_accepts_and_converts_jalali_input():
    form = DemoForm(data={"jalali_date": "1403-01-01"})
    assert form.is_valid()
    assert form.cleaned_data["jalali_date"] == to_jalali("1403-01-01")


def test_form_accepts_farsi_digit_input():
    form = DemoForm(data={"jalali_date": "۱۴۰۳-۰۱-۰۱"})
    assert form.is_valid()
    assert form.cleaned_data["jalali_date"] == to_jalali("1403-01-01")


def test_form_rejects_invalid_date():
    form = DemoForm(data={"jalali_date": "invalid"})
    assert not form.is_valid()


def test_invalid_date_form_rerenders_without_crashing():
    # Django re-renders a bound-but-invalid form with the raw submitted
    # string so the user can see and fix it. The widget must not crash
    # trying to parse that string as a Jalali date.
    form = DemoForm(data={"jalali_date": "1405-13-40"})
    assert not form.is_valid()
    rendered = form.as_p()
    assert "1405-13-40" in rendered

    form = DemoForm(data={"jalali_date": "not a date"})
    assert not form.is_valid()
    assert "not a date" in form.as_p()


class DemoAdmin(JalaliDateAdminMixin, admin.ModelAdmin):
    list_display = ("jalali_date", "jalali_datetime")


class DemoModel(models.Model):
    jalali_date = ModelJalaliDateField()
    jalali_datetime = ModelJalaliDateTimeField()

    class Meta:
        app_label = "test_django_integration"


def test_admin_mixin_adds_jalali_widget_and_media():
    model_field = DemoModel._meta.get_field("jalali_date")
    admin_instance = DemoAdmin(model=DemoModel, admin_site=admin.site)

    formfield = admin_instance.formfield_for_dbfield(model_field, request=None)

    assert formfield.widget.attrs["data-jalali-datepicker"] == "true"
    assert "jalali_suite/js/jalali-datepicker.js" in admin_instance.media._js
    assert "jalali_suite/css/jalali-datepicker.css" in admin_instance.media._css["all"]


def test_admin_date_widget_does_not_inherit_djangos_vdatefield_class():
    # Django's own formfield_overrides hands formfield_for_dbfield a plain
    # AdminDateWidget with class="vDateField" before our mixin replaces it.
    # If that class leaks onto our widget, Django's native calendar/"Today"
    # shortcut JS (which targets .vDateField) attaches to the field too and
    # writes a raw Gregorian date straight into it, bypassing conversion.
    model_field = DemoModel._meta.get_field("jalali_date")
    admin_instance = DemoAdmin(model=DemoModel, admin_site=admin.site)

    formfield = admin_instance.formfield_for_dbfield(model_field, request=None)

    assert formfield.widget.attrs["class"] == "jalali-suite-date"


def test_jalali_date_widget_declares_its_required_media():
    media = JalaliDateField().widget.media

    assert "jalali_suite/css/vazirmatn.css" in media._css["all"]
    assert "jalali_suite/css/jalali-datepicker.css" in media._css["all"]
    assert "jalali_suite/js/jalali-datepicker.js" in media._js


def test_admin_can_build_a_jalali_datetime_formfield():
    model_field = DemoModel._meta.get_field("jalali_datetime")
    admin_instance = DemoAdmin(model=DemoModel, admin_site=admin.site)

    formfield = admin_instance.formfield_for_dbfield(model_field, request=None)

    assert isinstance(formfield, SplitJalaliDateTimeField)
    assert formfield.widget.widgets[0].attrs["data-jalali-datepicker"] == "true"


def test_admin_datetime_widget_decompresses_jalali_values():
    model_field = DemoModel._meta.get_field("jalali_datetime")
    admin_instance = DemoAdmin(model=DemoModel, admin_site=admin.site)
    formfield = admin_instance.formfield_for_dbfield(model_field, request=None)

    assert formfield.widget.decompress(JalaliDateTime(1403, 1, 1, 12, 30)) == [
        "1403-01-01",
        datetime(2024, 3, 20, 12, 30).time(),
    ]


def test_datetime_widget_renders_its_subwidgets():
    rendered = JalaliSplitDateTimeWidget().render(
        "jalali_datetime", JalaliDateTime(1403, 1, 1, 12, 30)
    )

    assert 'name="jalali_datetime_0"' in rendered
    assert 'name="jalali_datetime_1"' in rendered
    assert "{'name':" not in rendered


def test_model_field_converts_between_jalali_and_database_values():
    model_field = DemoModel._meta.get_field("jalali_date")
    value = to_jalali("1403-01-01")

    assert model_field.get_prep_value(value).isoformat() == "2024-03-20"
    assert model_field.to_python(date(2024, 3, 20)) == value


def test_admin_list_display_always_uses_jalali_format():
    admin_instance = DemoAdmin(model=DemoModel, admin_site=admin.site)
    instance = DemoModel(jalali_date=to_jalali("1403-01-01"))

    fields = admin_instance.get_list_display(request=None)

    assert fields == ["get_jalali_jalali_date", "get_jalali_jalali_datetime"]
    assert getattr(admin_instance, fields[0])(instance) == "<bdi>1403/01/01</bdi>"
