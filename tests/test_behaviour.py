"""Lookups, form fields, widgets and the admin's read-only handling."""

from datetime import date, datetime
from datetime import timezone as dt_timezone

import jdatetime
import pytest
from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils import translation

from jalali_suite import widgets
from jalali_suite.forms import JalaliDateTimeField, SplitJalaliDateTimeField
from tests.testapp.models import Event, Ledger, Plain

UTC = dt_timezone.utc
NOWRUZ_1403 = date(2024, 3, 20)
NOON_UTC = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)  # 15:30 in Tehran


def model_admin_for(model):
    return admin.site._registry[model]


# --- __date lookup ----------------------------------------------------------


@pytest.mark.django_db
def test_date_lookup_accepts_jalali_values_and_uses_the_local_date():
    # 21:30 UTC on 19 March is 01:00 on 20 March in Tehran.
    inside = Event.objects.create(at=datetime(2024, 3, 19, 21, 30, tzinfo=UTC))
    Event.objects.create(at=datetime(2024, 3, 20, 21, 30, tzinfo=UTC))  # 21 March local

    assert list(Event.objects.filter(at__date=jdatetime.date(1403, 1, 1))) == [inside]
    assert list(Event.objects.filter(at__date="1403-01-01")) == [inside]
    assert list(Event.objects.filter(at__date=NOWRUZ_1403)) == [inside]
    assert Event.objects.filter(at__date__gte="1403-01-01").count() == 2
    assert Event.objects.filter(at__date__year=1403).count() == 2
    assert Event.objects.filter(at__date__year=1402).count() == 0


# --- forms and widgets ------------------------------------------------------


def test_single_datetime_field_renders_a_jalali_text_input():
    assert isinstance(JalaliDateTimeField().widget, widgets.JalaliDateTimeWidget)
    widget = widgets.JalaliDateTimeWidget()
    assert 'value="1403-01-01 15:30:00"' in widget.render("when", NOON_UTC)
    assert 'value="1403-01-01 15:30:00"' in widget.render("when", "1403/1/1 15:30")
    assert 'value="oops"' in widget.render("when", "oops")  # rejected input is echoed
    with translation.override("fa"):
        assert 'value="۱۴۰۳-۰۱-۰۱ ۱۵:۳۰:۰۰"' in widget.render("when", NOON_UTC)


def test_split_field_accepts_separate_input_formats():
    field = SplitJalaliDateTimeField(
        input_date_formats=["%d.%m.%Y"], input_time_formats=["%H.%M"]
    )
    assert field.clean(["01.01.1403", "15.30"]) == NOON_UTC
    with pytest.raises(forms.ValidationError):
        field.clean(["1403-01-01", "15:30:00"])


# --- admin: readonly fields, LIST_DISPLAY_AUTO_CONVERT ----------------------


@pytest.mark.django_db
def test_readonly_date_fields_are_shown_as_jalali_in_local_time(admin_client):
    ledger = Ledger.objects.create(title="x", opened=NOWRUZ_1403, closed=NOON_UTC)
    response = admin_client.get(reverse("admin:testapp_ledger_change", args=[ledger.pk]))
    html = response.content.decode()

    assert response.status_code == 200
    assert "<bdi>1403/01/01</bdi>" in html  # plain Django DateField, read-only
    assert "<bdi>1403/01/01 15:30:00</bdi>" in html  # Jalali datetime, local time
    assert "2024" not in html.split("<fieldset")[1]  # no Gregorian leftovers


@pytest.mark.django_db
def test_readonly_date_fields_work_on_the_add_page_and_keep_their_labels(admin_client):
    html = admin_client.get(reverse("admin:testapp_ledger_add")).content.decode()

    assert "Opened" in html and "Closed" in html
    assert 'name="opened"' not in html and 'name="closed_0"' not in html


@pytest.mark.django_db
def test_readonly_fields_cannot_be_edited_through_post(admin_client):
    ledger = Ledger.objects.create(title="x", opened=NOWRUZ_1403)
    response = admin_client.post(
        reverse("admin:testapp_ledger_change", args=[ledger.pk]),
        {"title": "y", "opened": "1404-01-01"},
    )
    assert response.status_code == 302
    ledger.refresh_from_db()
    assert ledger.title == "y" and ledger.opened == NOWRUZ_1403


def test_the_layout_uses_the_same_callables_as_the_readonly_list():
    ma = model_admin_for(Ledger)
    readonly = ma.get_readonly_fields(request=None)
    layout = ma.get_fieldsets(request=None)[0][1]["fields"]

    assert all(callable(item) for item in readonly)
    assert layout[0] == "title"
    assert layout[1] is readonly[0] and layout[2] is readonly[1]


def test_auto_convert_can_be_switched_off(settings):
    settings.JALALI_SUITE = {"LIST_DISPLAY_AUTO_CONVERT": False}

    ma = model_admin_for(Plain)
    assert ma.get_list_display(request=None) == ["title", "day", "at"]
    ledger_admin = model_admin_for(Ledger)
    assert list(ledger_admin.get_readonly_fields(request=None)) == ["opened", "closed"]
