from datetime import date

from django import forms
from django.contrib import admin
from django.db import models

from jalali_suite.admin import JalaliDateAdminMixin
from jalali_suite.forms import JalaliDateField
from jalali_suite.models import JalaliDateField as ModelJalaliDateField
from jalali_suite.utils import to_jalali


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


class DemoAdmin(JalaliDateAdminMixin, admin.ModelAdmin):
    pass


class DemoModel(models.Model):
    jalali_date = ModelJalaliDateField()

    class Meta:
        app_label = "test_django_integration"


def test_admin_mixin_adds_jalali_widget_and_media():
    model_field = DemoModel._meta.get_field("jalali_date")
    admin_instance = DemoAdmin(model=DemoModel, admin_site=admin.site)

    formfield = admin_instance.formfield_for_dbfield(model_field, request=None)

    assert formfield.widget.attrs["data-jalali-datepicker"] == "true"
    assert "jalali_suite/js/jalali-datepicker.js" in admin_instance.media._js
    assert "jalali_suite/css/jalali-datepicker.css" in admin_instance.media._css["all"]


def test_model_field_converts_between_jalali_and_database_values():
    model_field = DemoModel._meta.get_field("jalali_date")
    value = to_jalali("1403-01-01")

    assert model_field.get_prep_value(value).isoformat() == "2024-03-20"
    assert model_field.to_python(date(2024, 3, 20)) == value
