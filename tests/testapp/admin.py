from django.contrib import admin

from jalali_suite.admin import (
    JalaliDateFieldListFilter,
    JalaliDateModelAdmin,
    JalaliDateTabularInline,
)

from .models import Event, Ledger, Plain, PlainNote


@admin.register(Event)
class EventAdmin(JalaliDateModelAdmin):
    fields = ("title", "day", "at")
    list_display = ("title", "day", "at")
    list_filter = ("day", "at")


class PlainNoteInline(JalaliDateTabularInline):
    model = PlainNote
    extra = 1
    jalali_widgets_for_gregorian_fields = True


@admin.register(Plain)
class PlainAdmin(JalaliDateModelAdmin):
    jalali_widgets_for_gregorian_fields = True  # opt in: plain columns, shown as Jalali
    list_display = ("title", "day", "at")
    list_filter = (("day", JalaliDateFieldListFilter),)
    inlines = [PlainNoteInline]


@admin.register(Ledger)
class LedgerAdmin(JalaliDateModelAdmin):
    jalali_widgets_for_gregorian_fields = True
    fields = ("title", "opened", "closed")
    readonly_fields = ("opened", "closed")
    list_display = ("title", "opened")
