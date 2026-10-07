from django.conf import settings
from django.core.signals import setting_changed

DEFAULTS = {
    "DATE_FORMAT": "%Y/%m/%d",
    "DATETIME_FORMAT": "%Y/%m/%d %H:%M:%S",
    # Show Jalali text for date columns in admin list_display and readonly fields.
    "LIST_DISPLAY_AUTO_CONVERT": True,
}


class SuiteSettings:
    @property
    def user_settings(self):
        if not settings.configured:
            return {}
        return getattr(settings, "JALALI_SUITE", {})

    def get(self, name):
        if name not in DEFAULTS:
            raise AttributeError(f"Invalid Jalali Suite setting: {name}")
        return self.user_settings.get(name, DEFAULTS[name])

    def reload(self):
        pass


jalali_settings = SuiteSettings()


def reload_settings(*, setting, **kwargs):
    if setting == "JALALI_SUITE":
        jalali_settings.reload()


setting_changed.connect(reload_settings)
