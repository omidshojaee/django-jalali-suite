from django.db import models
from django.utils import timezone

from jalali_suite.models import JalaliDateField, JalaliDateTimeField


class Event(models.Model):
    """Uses the suite's Jalali model fields."""

    title = models.CharField(max_length=50, blank=True)
    day = JalaliDateField(null=True, blank=True)
    at = JalaliDateTimeField(null=True, blank=True)
    created = JalaliDateTimeField(default=timezone.now)
    stamped = JalaliDateTimeField(auto_now_add=True)
    touched = JalaliDateField(auto_now=True)


class Plain(models.Model):
    """Uses ordinary Django date fields, shown as Jalali by the admin mixin."""

    title = models.CharField(max_length=50, blank=True)
    day = models.DateField(null=True, blank=True)
    at = models.DateTimeField(null=True, blank=True)


class PlainNote(models.Model):
    plain = models.ForeignKey(Plain, on_delete=models.CASCADE, related_name="notes")
    text = models.CharField(max_length=50, blank=True)
    when = models.DateField(null=True, blank=True)


class Ledger(models.Model):
    """The admin shows its date columns read-only."""

    title = models.CharField(max_length=50, blank=True)
    opened = models.DateField(null=True, blank=True)  # plain Django column
    closed = JalaliDateTimeField(null=True, blank=True)
