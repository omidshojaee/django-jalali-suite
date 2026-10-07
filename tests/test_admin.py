import datetime as dt
from datetime import date, datetime
from datetime import timezone as dt_timezone

import jdatetime
import pytest
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from jalali_suite import admin as jalali_admin
from jalali_suite.admin import (
    JalaliDateAdminMixin,
    JalaliDateFieldListFilter,
    JalaliDateModelAdmin,
)
from jalali_suite.forms import JalaliDateField, SplitJalaliDateTimeField
from jalali_suite.utils import jalali_range
from jalali_suite.widgets import AdminJalaliDateWidget, AdminJalaliSplitDateTimeWidget
from tests.testapp.models import Event, Plain, PlainNote

UTC = dt_timezone.utc
NOON_UTC = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)  # 15:30 in Tehran


def model_admin(model):
    return admin.site._registry[model]


# --- form fields and widgets ------------------------------------------------


@pytest.mark.parametrize("model", [Event, Plain])
def test_date_fields_get_the_jalali_widget_for_both_field_kinds(model):
    ma = model_admin(model)

    day = ma.formfield_for_dbfield(model._meta.get_field("day"), request=None)
    assert isinstance(day, JalaliDateField)
    assert isinstance(day.widget, AdminJalaliDateWidget)
    assert day.widget.attrs["class"] == "jalali-suite-date"  # no vDateField leak

    at = ma.formfield_for_dbfield(model._meta.get_field("at"), request=None)
    assert isinstance(at, SplitJalaliDateTimeField)
    assert isinstance(at.widget, AdminJalaliSplitDateTimeWidget)
    assert at.widget.widgets[0].attrs["data-jalali-datepicker"] == "true"


def test_gregorian_fields_can_opt_out():
    class Quiet(JalaliDateModelAdmin):
        jalali_widgets_for_gregorian_fields = False

    ma = Quiet(Plain, admin.site)
    plain = ma.formfield_for_dbfield(Plain._meta.get_field("day"), request=None)
    assert isinstance(plain.widget.widget if hasattr(plain.widget, "widget") else plain.widget, AdminDateWidget)
    jalali = Quiet(Event, admin.site).formfield_for_dbfield(
        Event._meta.get_field("day"), request=None
    )
    assert isinstance(jalali.widget, AdminJalaliDateWidget)  # Jalali model fields always


def test_other_fields_are_untouched():
    field = model_admin(Event).formfield_for_dbfield(
        Event._meta.get_field("title"), request=None
    )
    assert field.__class__.__name__ == "CharField"


def test_media_includes_scripts_styles_and_the_bundled_font():
    media = model_admin(Event).media
    assert "jalali_suite/js/jalali-datepicker.js" in media._js
    assert "jalali_suite/css/jalali-datepicker.css" in media._css["all"]
    assert "jalali_suite/css/vazirmatn.css" in media._css["all"]


def test_migration_aliases_exist():
    assert jalali_admin.ModelAdminJalaliMixin is JalaliDateAdminMixin
    assert jalali_admin.TabularInlineJalaliMixin is JalaliDateAdminMixin
    assert jalali_admin.StackedInlineJalaliMixin is JalaliDateAdminMixin


# --- list display -----------------------------------------------------------


@pytest.mark.parametrize("model", [Event, Plain])
def test_list_display_columns_are_sortable_jalali_text(model):
    ma = model_admin(model)
    columns = ma.get_list_display(request=None)

    assert columns[0] == "title"  # non-date columns are left alone
    day_column, at_column = columns[1], columns[2]
    assert callable(day_column) and callable(at_column)
    assert day_column.admin_order_field == "day"
    assert at_column.admin_order_field == "at"
    assert day_column.__name__ == "jalali_day"

    obj = model(day=date(2024, 3, 20), at=NOON_UTC)
    assert day_column(obj) == "<bdi>1403/01/01</bdi>"
    assert at_column(obj) == "<bdi>1403/01/01 15:30:00</bdi>"
    assert day_column(model()) is None


# --- date filter ------------------------------------------------------------


def make_filter(model, field_name):
    ma = model_admin(model)
    request = RequestFactory().get("/")
    return JalaliDateFieldListFilter(
        model._meta.get_field(field_name), request, {}, model, ma, field_name
    )


def test_jalali_model_fields_get_the_jalali_filter_automatically():
    from django.contrib.admin.filters import FieldListFilter

    event_filter = FieldListFilter.create(
        Event._meta.get_field("day"),
        RequestFactory().get("/"),
        {},
        Event,
        model_admin(Event),
        "day",
    )
    assert isinstance(event_filter, JalaliDateFieldListFilter)


def test_filter_uses_jalali_month_and_year_boundaries():
    flt = make_filter(Event, "day")
    jtoday = jdatetime.date.fromgregorian(date=timezone.localdate())
    month_start, next_month = jalali_range(jtoday.year, jtoday.month)
    year_start, next_year = jalali_range(jtoday.year)
    links = {str(label): params for label, params in flt.links}

    since, until = flt.lookup_kwarg_since, flt.lookup_kwarg_until
    assert links["Today"][since] == jtoday.togregorian()
    assert links["This month"] == {since: month_start, until: next_month}
    assert links["This year"] == {since: year_start, until: next_year}


def test_filter_on_datetime_fields_uses_local_midnight_boundaries():
    flt = make_filter(Event, "at")
    jtoday = jdatetime.date.fromgregorian(date=timezone.localdate())
    year_start, _ = jalali_range(jtoday.year)
    since = flt.lookup_kwarg_since
    start = dict((str(label), params) for label, params in flt.links)["This year"][since]

    assert timezone.is_aware(start)
    assert timezone.localtime(start).date() == year_start
    assert timezone.localtime(start).time() == dt.time(0, 0)


def test_filter_keeps_null_choices_for_nullable_fields():
    labels = [str(label) for label, _ in make_filter(Event, "day").links]
    assert labels == [
        "Any date",
        "Today",
        "Past 7 days",
        "This month",
        "This year",
        "No date",
        "Has date",
    ]


# --- end to end through the admin site --------------------------------------


@pytest.mark.django_db
def test_changelist_renders_jalali_values_and_filters(admin_client):
    Event.objects.create(title="a", day=date(2024, 3, 20), at=NOON_UTC)
    Plain.objects.create(title="b", day=date(2024, 3, 20), at=NOON_UTC)

    for name in ("event", "plain"):
        response = admin_client.get(reverse(f"admin:testapp_{name}_changelist"))
        assert response.status_code == 200
        html = response.content.decode()
        assert "1403/01/01" in html
        assert "<bdi>1403/01/01 15:30:00</bdi>" in html
        assert "?o=" in html  # the Jalali columns remain sortable

    # Filter applied through the query string (what the filter links produce).
    response = admin_client.get(
        reverse("admin:testapp_event_changelist"),
        {"day__gte": "2024-03-20", "day__lt": "2025-03-21"},
    )
    assert response.status_code == 200
    assert response.context["cl"].result_count == 1


@pytest.mark.django_db
def test_changelist_sorting_by_a_jalali_column(admin_client):
    Event.objects.create(title="later", day=date(2025, 1, 1))
    Event.objects.create(title="earlier", day=date(2024, 1, 1))

    response = admin_client.get(reverse("admin:testapp_event_changelist"), {"o": "2"})
    assert response.status_code == 200
    assert [e.title for e in response.context["cl"].result_list] == ["earlier", "later"]


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["event", "plain"])
def test_add_page_renders_jalali_widgets_only(admin_client, name):
    response = admin_client.get(reverse(f"admin:testapp_{name}_add"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "jalali-suite-date" in html
    assert "vDateField" not in html  # Django's Gregorian calendar must not attach
    assert "jalali_suite/js/jalali-datepicker.js" in html


@pytest.mark.django_db
def test_change_page_shows_saved_values_as_jalali_local_time(admin_client):
    event = Event.objects.create(day=date(2024, 3, 20), at=NOON_UTC)
    response = admin_client.get(reverse("admin:testapp_event_change", args=[event.pk]))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'value="1403-01-01"' in html
    assert 'value="15:30:00"' in html


@pytest.mark.django_db
def test_saving_a_jalali_model_through_the_admin(admin_client):
    response = admin_client.post(
        reverse("admin:testapp_event_add"),
        {"title": "x", "day": "1403-01-01", "at_0": "1403-01-01", "at_1": "15:30:00"},
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    event = Event.objects.get()
    assert event.day == jdatetime.date(1403, 1, 1)
    assert event.at == NOON_UTC


INLINE_MANAGEMENT = {
    "notes-TOTAL_FORMS": "1",
    "notes-INITIAL_FORMS": "0",
    "notes-MIN_NUM_FORMS": "0",
    "notes-MAX_NUM_FORMS": "1000",
}


@pytest.mark.django_db
def test_saving_plain_django_fields_through_the_jalali_widgets(admin_client):
    response = admin_client.post(
        reverse("admin:testapp_plain_add"),
        {
            "title": "x",
            "day": "1403-01-01",
            "at_0": "1403-01-01",
            "at_1": "15:30:00",
            **INLINE_MANAGEMENT,
            "notes-0-text": "",
            "notes-0-when": "",
        },
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    plain = Plain.objects.get()
    assert plain.day == date(2024, 3, 20)
    assert type(plain.day) is date  # plain columns keep standard types
    assert plain.at == NOON_UTC
    # An untouched extra inline row must not be saved (needs has_changed to work).
    assert PlainNote.objects.count() == 0


@pytest.mark.django_db
def test_inline_rows_with_jalali_dates_are_saved(admin_client):
    response = admin_client.post(
        reverse("admin:testapp_plain_add"),
        {
            "title": "x",
            "day": "",
            "at_0": "",
            "at_1": "",
            **INLINE_MANAGEMENT,
            "notes-0-text": "hello",
            "notes-0-when": "1403-01-01",
        },
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    note = PlainNote.objects.get()
    assert note.when == date(2024, 3, 20)


@pytest.mark.django_db
def test_invalid_jalali_date_is_reported_and_redisplayed(admin_client):
    response = admin_client.post(
        reverse("admin:testapp_event_add"),
        {"title": "x", "day": "1403-13-40", "at_0": "", "at_1": ""},
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert "valid Jalali date" in html
    assert "1403-13-40" in html
    assert Event.objects.count() == 0
