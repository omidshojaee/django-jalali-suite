"""Extra admin sites used to test date_hierarchy without touching the main one."""

from django.contrib import admin
from django.contrib.admin import AdminSite

from jalali_suite.admin import JalaliDateModelAdmin

from .models import Event, Plain

site = AdminSite(name="hier")
bare_site = AdminSite(name="bare")


class EventHierarchyAdmin(JalaliDateModelAdmin):
    date_hierarchy = "at"
    list_display = ("title",)


class PlainHierarchyAdmin(JalaliDateModelAdmin):
    jalali_widgets_for_gregorian_fields = True
    date_hierarchy = "day"
    list_display = ("title",)


class BareEventAdmin(admin.ModelAdmin):
    """No mixin: the system check must warn about this one."""

    date_hierarchy = "day"


site.register(Event, EventHierarchyAdmin)
site.register(Plain, PlainHierarchyAdmin)
bare_site.register(Event, BareEventAdmin)
