from datetime import date, datetime, time
from datetime import timezone as dt_timezone

import jdatetime
import pytest
from django import forms
from django.utils import translation

from jalali_suite.forms import (
    JalaliDateField,
    JalaliDateTimeField,
    SplitJalaliDateTimeField,
)
from jalali_suite.widgets import JalaliDateWidget, JalaliSplitDateTimeWidget
from tests.testapp.models import Event

UTC = dt_timezone.utc
NOON_UTC = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)  # 15:30 in Tehran


class DateForm(forms.Form):
    when = JalaliDateField()


class DateTimeForm(forms.Form):
    when = SplitJalaliDateTimeField()


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["day", "at"]


# --- JalaliDateField --------------------------------------------------------


@pytest.mark.parametrize("text", ["1403-01-01", "1403/1/1", "۱۴۰۳-۰۱-۰۱", " 1403-01-01 "])
def test_date_field_cleans_to_a_standard_date(text):
    form = DateForm(data={"when": text})
    assert form.is_valid(), form.errors
    cleaned = form.cleaned_data["when"]
    assert cleaned == date(2024, 3, 20)
    assert type(cleaned) is date


@pytest.mark.parametrize("text", ["invalid", "1403-13-01", "1403-07-31", ""])
def test_date_field_rejects_bad_input(text):
    assert not DateForm(data={"when": text}).is_valid()


def test_date_field_reads_input_as_jalali_even_for_gregorian_looking_years():
    form = DateForm(data={"when": "2024-03-20"})
    assert form.is_valid()
    assert form.cleaned_data["when"] == jdatetime.date(2024, 3, 20).togregorian()


def test_date_field_honours_input_formats():
    field = JalaliDateField(input_formats=["%d.%m.%Y"])
    assert field.clean("01.01.1403") == date(2024, 3, 20)
    with pytest.raises(forms.ValidationError):
        field.clean("1403-01-01")


def test_date_field_has_changed_compares_cleaned_values():
    field = JalaliDateField(required=False)
    assert not field.has_changed("1403-01-01", "۱۴۰۳/۰۱/۰۱")
    assert not field.has_changed(date(2024, 3, 20), "1403-01-01")
    assert not field.has_changed(jdatetime.date(1403, 1, 1), "1403-01-01")
    assert not field.has_changed(None, "")
    assert field.has_changed("1403-01-01", "1403-01-02")
    assert field.has_changed(None, "1403-01-01")
    assert field.has_changed("1403-01-01", "garbage")


def test_date_widget_renders_jalali_text_for_every_value_type():
    widget = JalaliDateWidget()
    for value in (date(2024, 3, 20), jdatetime.date(1403, 1, 1), "1403/1/1"):
        assert 'value="1403-01-01"' in widget.render("when", value)
    assert 'data-jalali-datepicker="true"' in widget.render("when", None)


def test_invalid_date_form_rerenders_the_raw_input():
    for raw in ("1405-13-40", "not a date"):
        form = DateForm(data={"when": raw})
        assert not form.is_valid()
        assert raw in form.as_p()


def test_date_widget_uses_farsi_digits_when_the_language_does():
    with translation.override("fa"):
        rendered = JalaliDateWidget().render("when", date(2024, 3, 20))
    assert 'value="۱۴۰۳-۰۱-۰۱"' in rendered


# --- single-input datetime --------------------------------------------------


def test_datetime_field_cleans_to_an_aware_datetime():
    cleaned = JalaliDateTimeField().clean("۱۴۰۳-۰۱-۰۱ ۱۵:۳۰:۰۰")
    assert cleaned == NOON_UTC
    assert cleaned.utcoffset() is not None


def test_datetime_field_rejects_date_only_input():
    with pytest.raises(forms.ValidationError):
        JalaliDateTimeField().clean("1403-01-01")


def test_datetime_field_has_changed():
    field = JalaliDateTimeField(required=False)
    assert not field.has_changed(NOON_UTC, "1403-01-01 15:30:00")
    assert field.has_changed(NOON_UTC, "1403-01-01 15:31:00")


# --- split datetime ---------------------------------------------------------


def test_split_field_cleans_wall_clock_input_as_local_time():
    cleaned = SplitJalaliDateTimeField().clean(["1403-01-01", "15:30:00"])
    assert cleaned == NOON_UTC
    assert cleaned.utcoffset().total_seconds() == 3.5 * 3600


def test_split_field_accepts_farsi_digits_in_both_parts():
    cleaned = SplitJalaliDateTimeField().clean(["۱۴۰۳-۰۱-۰۱", "۱۵:۳۰:۰۰"])
    assert cleaned == NOON_UTC


def test_split_field_required_and_optional():
    with pytest.raises(forms.ValidationError):
        SplitJalaliDateTimeField().clean(["", ""])
    assert SplitJalaliDateTimeField(required=False).clean(["", ""]) is None


def test_split_widget_decompresses_to_local_wall_clock():
    widget = JalaliSplitDateTimeWidget()
    assert widget.decompress(NOON_UTC) == ["1403-01-01", time(15, 30)]
    assert widget.decompress(jdatetime.datetime(1403, 1, 1, 15, 30)) == [
        "1403-01-01",
        time(15, 30),
    ]
    assert widget.decompress(None) == [None, None]


def test_split_widget_renders_both_subwidgets():
    rendered = JalaliSplitDateTimeWidget().render("when", NOON_UTC)
    assert 'name="when_0"' in rendered and 'value="1403-01-01"' in rendered
    assert 'name="when_1"' in rendered and 'value="15:30:00"' in rendered


def test_split_widget_time_follows_the_site_language():
    with translation.override("fa"):
        rendered = JalaliSplitDateTimeWidget().render("when", NOON_UTC)
        cleaned = SplitJalaliDateTimeField().clean(["1403-01-01", "۱۵:۳۰:۰۰"])
    assert 'value="۱۵:۳۰:۰۰"' in rendered
    assert cleaned == NOON_UTC
    with translation.override("en"):
        assert 'value="15:30:00"' in JalaliSplitDateTimeWidget().render("when", NOON_UTC)


# --- ModelForm --------------------------------------------------------------


@pytest.mark.django_db
def test_model_form_round_trip():
    form = EventForm(
        data={"day": "1403-01-01", "at_0": "1403-01-01", "at_1": "15:30:00"}
    )
    assert form.is_valid(), form.errors
    event = form.save()

    event.refresh_from_db()
    assert event.day == jdatetime.date(1403, 1, 1)
    assert event.at == NOON_UTC
    assert (event.at.hour, event.at.minute) == (15, 30)


@pytest.mark.django_db
def test_model_form_shows_saved_values_and_sees_no_change_when_resubmitted():
    event = Event.objects.create(day=date(2024, 3, 20), at=NOON_UTC)
    data = {"day": "1403-01-01", "at_0": "1403-01-01", "at_1": "15:30:00"}

    form = EventForm(data=data, instance=event)
    assert form.is_valid(), form.errors
    assert not form.has_changed()  # regression: used to report a change always

    rendered = EventForm(instance=event).as_p()
    assert 'value="1403-01-01"' in rendered
    assert 'value="15:30:00"' in rendered

    changed = EventForm(data={**data, "day": "1403-01-02"}, instance=event)
    assert changed.has_changed()
    assert changed.changed_data == ["day"]


@pytest.mark.django_db
def test_model_form_rejects_invalid_jalali_input():
    form = EventForm(data={"day": "1403-13-01", "at_0": "x", "at_1": "y"})
    assert not form.is_valid()
    assert {"day", "at"} <= set(form.errors)
