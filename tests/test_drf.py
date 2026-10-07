from datetime import date, datetime
from datetime import timezone as dt_timezone

import jdatetime
import pytest
from rest_framework import serializers

from jalali_suite.serializers import (
    JalaliDateSerializerField,
    JalaliDateTimeSerializerField,
    JalaliModelSerializer,
)
from tests.testapp.models import Event, Plain

UTC = dt_timezone.utc
NOON_UTC = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)  # 15:30 in Tehran


class EventSerializer(JalaliModelSerializer):
    class Meta:
        model = Event
        fields = ("id", "day", "at")


class PlainSerializer(serializers.ModelSerializer):
    day = JalaliDateSerializerField(required=False, allow_null=True)
    at = JalaliDateTimeSerializerField(required=False, allow_null=True)

    class Meta:
        model = Plain
        fields = ("id", "day", "at")


def test_model_serializer_maps_jalali_model_fields_automatically():
    fields = EventSerializer().fields
    assert isinstance(fields["day"], JalaliDateSerializerField)
    assert isinstance(fields["at"], JalaliDateTimeSerializerField)
    assert not fields["day"].required and fields["day"].allow_null


@pytest.mark.parametrize(
    "day, at",
    [
        ("1403-01-01", "1403-01-01T15:30:00"),
        ("۱۴۰۳-۰۱-۰۱", "۱۴۰۳-۰۱-۰۱T۱۵:۳۰:۰۰"),
        ("1403/01/01", "1403-01-01T12:00:00Z"),
        ("2024-03-20", "2024-03-20T12:00:00+00:00"),  # Gregorian clients work too
    ],
)
def test_input_is_cleaned_to_standard_values(day, at):
    serializer = EventSerializer(data={"day": day, "at": at})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["day"] == date(2024, 3, 20)
    assert serializer.validated_data["at"] == NOON_UTC
    assert type(serializer.validated_data["day"]) is date


def test_gregorian_looking_input_is_not_misread_as_a_jalali_year():
    serializer = EventSerializer(data={"day": "2024-03-20"})
    assert serializer.is_valid()
    assert serializer.validated_data["day"] == date(2024, 3, 20)


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"day": "nonsense"}, "day"),
        ({"day": "1403-13-01"}, "day"),
        ({"at": "1403-01-01"}, "at"),  # a datetime needs a time
        ({"at": "nonsense"}, "at"),
    ],
)
def test_bad_input_is_rejected_with_a_message(payload, field):
    serializer = EventSerializer(data=payload)
    assert not serializer.is_valid()
    assert "valid Jalali" in str(serializer.errors[field])


def test_null_is_allowed_for_nullable_fields():
    serializer = EventSerializer(data={"day": None, "at": None})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data == {"day": None, "at": None}


@pytest.mark.django_db
def test_representation_is_jalali_iso_in_the_local_time_zone():
    event = Event.objects.create(day=date(2024, 3, 20), at=NOON_UTC)
    data = EventSerializer(Event.objects.get(pk=event.pk)).data
    assert data["day"] == "1403-01-01"
    assert data["at"] == "1403-01-01T15:30:00+03:30"


@pytest.mark.django_db
def test_unsaved_gregorian_assignments_are_represented_the_same_way():
    event = Event(day=date(2024, 3, 20), at=NOON_UTC)
    data = EventSerializer(event).data
    assert (data["day"], data["at"]) == ("1403-01-01", "1403-01-01T15:30:00+03:30")


@pytest.mark.django_db
def test_create_and_update_round_trip_through_the_database():
    serializer = EventSerializer(
        data={"day": "1403-01-01", "at": "1403-01-01T15:30:00+03:30"}
    )
    assert serializer.is_valid(), serializer.errors
    event = serializer.save()

    stored = Event.objects.get(pk=event.pk)
    assert stored.day == jdatetime.date(1403, 1, 1)
    assert stored.at == NOON_UTC

    update = EventSerializer(stored, data={"day": "1404-01-01"}, partial=True)
    assert update.is_valid(), update.errors
    update.save()
    assert Event.objects.get(pk=event.pk).day == jdatetime.date(1404, 1, 1)
    assert Event.objects.get(pk=event.pk).at == NOON_UTC  # untouched


@pytest.mark.django_db
def test_fields_work_on_plain_django_date_columns():
    serializer = PlainSerializer(data={"day": "1403-01-01", "at": "1403-01-01T12:00:00Z"})
    assert serializer.is_valid(), serializer.errors
    plain = serializer.save()

    plain.refresh_from_db()
    assert plain.day == date(2024, 3, 20)
    assert plain.at == NOON_UTC
    assert PlainSerializer(plain).data["day"] == "1403-01-01"
