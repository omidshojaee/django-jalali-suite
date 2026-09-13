from datetime import datetime

from django.db import models

from jalali_suite.models import JalaliDateField, JalaliDateTimeField
from jalali_suite.serializers import JalaliModelSerializer


class ApiRecord(models.Model):
    date = JalaliDateField()
    timestamp = JalaliDateTimeField()

    class Meta:
        app_label = "test_drf"


class ApiRecordSerializer(JalaliModelSerializer):
    class Meta:
        model = ApiRecord
        fields = ("date", "timestamp")


def test_model_serializer_uses_jalali_fields_automatically():
    serializer = ApiRecordSerializer(
        data={
            "date": "۱۴۰۳-۰۱-۰۱",
            "timestamp": "۱۴۰۳-۰۱-۰۱T12:30:00",
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["date"].isoformat == "1403-01-01"
    assert serializer.validated_data["timestamp"].isoformat == "1403-01-01T12:30:00"


def test_model_serializer_represents_gregorian_values_as_jalali():
    instance = ApiRecord(
        date=datetime(2024, 3, 20).date(),
        timestamp=datetime(2024, 3, 20, 12, 30),
    )

    data = ApiRecordSerializer(instance).data

    assert data == {
        "date": "1403-01-01",
        "timestamp": "1403-01-01T12:30:00",
    }
